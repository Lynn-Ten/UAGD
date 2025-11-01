import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.utils import get_laplacian, to_dense_adj
import numpy as np
from scipy.sparse.linalg import eigsh
from torch_geometric.graphgym.cmd_args import parse_args
import os
from load_datas import load_mat,load_truth
from sklearn.metrics import roc_auc_score
import torch.nn.functional as F
class LapPosEncoder(nn.Module):
    def __init__(self, dim, normalization='sym'):
        super().__init__()
        self.pos_enc_dim = dim
        self.normalization = normalization
    
    def forward(self, edge_index, num_nodes):
        # Get Laplacian
        edge_index, edge_attr = get_laplacian(
            edge_index, normalization=self.normalization,
            num_nodes=num_nodes
        )
    
        L = to_dense_adj(edge_index, edge_attr=edge_attr)[0]
        EigVal, EigVec = torch.linalg.eigh(L)
        idx = torch.argsort(EigVal)
        EigVec = EigVec[:, idx]
        return EigVec[:, 1:self.pos_enc_dim+1]

class GraphTransformerLayer(nn.Module):
    def __init__(self, d_model, nhead, dim_feedforward=2048, dropout=0.9):
        super().__init__()
        self.self_attn = nn.MultiheadAttention(d_model, nhead, dropout=dropout)
        
        self.linear1 = nn.Linear(d_model, dim_feedforward)
        self.linear2 = nn.Linear(dim_feedforward, d_model)
        
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        
        self.dropout = nn.Dropout(dropout)
        self.dropout1 = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout)
        
        self.activation = nn.ReLU()

    def forward(self, src, pos_encoding, src_mask=None, src_key_padding_mask=None):
        # Add positional encoding
        src = src + pos_encoding
        
        # Self attention
        src2, _ = self.self_attn(src, src, src, 
                                attn_mask=src_mask,
                                key_padding_mask=src_key_padding_mask)
        src = src + self.dropout1(src2)
        src = self.norm1(src)
        
        # Feedforward
        src2 = self.linear2(self.dropout(self.activation(self.linear1(src))))
        src = src + self.dropout2(src2)
        src = self.norm2(src)
        
        return src

class TAD(nn.Module):
    def __init__(self, in_channels, hidden_channels=64, num_layers=
                 4, heads=4, dropout=0.9, pos_enc_dim=8):
        super().__init__()
        
        self.pos_encoder = LapPosEncoder(pos_enc_dim)
        
        # Node feature embedding
        self.node_encoder = nn.Linear(in_channels, hidden_channels)
        self.pos_embedding = nn.Linear(pos_enc_dim, hidden_channels)
        
        # Transformer encoder layers
        self.layers = nn.ModuleList([
            GraphTransformerLayer(
                hidden_channels, heads, 
                hidden_channels * 4, 
                dropout
            ) for _ in range(num_layers)
        ])
        
        # VAE components
        self.mu = nn.Linear(hidden_channels, hidden_channels)
        self.logvar = nn.Linear(hidden_channels, hidden_channels)
        
        # Decoders
        self.node_decoder = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels),
            nn.ReLU(),
            nn.Linear(hidden_channels, in_channels)
        )
        
        # self.edge_decoder = nn.Sequential(
        #     nn.Linear(hidden_channels*2, hidden_channels),
        #     nn.ReLU(),
        #     nn.Linear(hidden_channels, hidden_channels),
        #     nn.Sigmoid()
        # )
        self.edge_decoder = nn.Bilinear(in1_features=hidden_channels, 
                               in2_features=hidden_channels, 
                               out_features=1, 
                               bias=True)

    def encode(self, x, edge_index, batch=None):
        # Compute positional encoding
        num_nodes = x.size(0)
        pos_enc = self.pos_encoder(edge_index, num_nodes)
        pos_enc = self.pos_embedding(pos_enc) #[NumNode,hidden]
        
        # Encode node features
        x = self.node_encoder(x)
        
        # Transformer encoding (B x N x D -> N x B x D)
        x = x.unsqueeze(1)  # Add batch dimension if not batched
        pos_enc = pos_enc.unsqueeze(1)
        
        # Apply transformer layers
        for layer in self.layers:
            x = layer(x, pos_enc)
            
        # Pool to graph representation
        # x = x.mean(dim=0) #[1, hidden]
        x = x.squeeze(1)  
        mu = self.mu(x)  # [num_nodes, hidden_dim]
        logvar = self.logvar(x)  # [num_nodes, hidden_dim]
        # VAE encoding
        return mu, logvar

    def reparameterize(self, mu, logvar):
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        else:
            return mu

    def decode(self, z, num_nodes):
        # Decode node features
        node_features = self.node_decoder(z)
        #node_features = self.node_decoder(z.expand(num_nodes, -1))
        
        # # Create node pairs for edge prediction
        # node_pairs = torch.cartesian_prod(torch.arange(num_nodes), torch.arange(num_nodes))
        # # print("node_pairs:",node_pairs.shape)
        # # print("num_nodes:",num_nodes)
        # # Get latent representations for node pairs
        # # print(node_pairs.shape)
        # # print(z.shape)
        # z_i = z[:,node_pairs[:, 0]]
        # z_j = z[:,node_pairs[:, 1]]
        # pair_repr = torch.cat([z_i, z_j], dim=-1)
        
        # pair_repr = pair_repr.view(num_nodes,num_nodes*2)
        # # print(pair_repr.shape)
        # # Predict edges
        # edge_pred = self.edge_decoder(pair_repr)

        edge_logits = torch.matmul(z, self.edge_decoder.weight)  # [num_nodes, latent] @ [latent, latent] -> [num_nodes, latent]
        edge_logits = torch.matmul(edge_logits, z.T)  # [num_nodes, latent] @ [latent, num_nodes] -> [num_nodes, num_nodes]
        edge_pred = torch.sigmoid(edge_logits + self.edge_decoder.bias)
            
        return node_features, edge_pred, None

    def forward(self, x, edge_index, batch=None):
        # Encode
        mu, logvar = self.encode(x, edge_index, batch)
        
        # Sample latent
        z = self.reparameterize(mu, logvar)
        
        # Decode
        x_recon, edge_pred, node_pairs = self.decode(z, x.size(0))
        
        return x_recon, edge_pred, node_pairs, mu, logvar



def compute_loss(model, x, edge_index):
    x_recon, edge_pred, _, mu, logvar = model(x, edge_index)
    pred_adj = edge_pred.squeeze()
    recon_loss = F.mse_loss(x_recon, x)
    true_adj = to_dense_adj(edge_index, max_num_nodes=x.size(0))[0]
    edge_loss = F.mse_loss(pred_adj, true_adj)
    total_loss = recon_loss * 0.5 + edge_loss * 0.5 

    node_mse = torch.sum((x - x_recon).pow(2), dim=1)  # [num_nodes]
    edge_mse = torch.sum((true_adj - pred_adj).pow(2), dim=1)  # [num_nodes] 
    anomaly_scores = node_mse + edge_mse
    
    return total_loss, recon_loss, edge_loss, None, anomaly_scores

def train_epoch(model, optimizer, data):
    model.train()
    total_loss = 0
    
    for i in range(50):
        optimizer.zero_grad()
        loss, _, _, iou ,anomaly_scores= compute_loss(model, data.x, data.edge_index)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        total_loss += loss.item()
        #print('acc:',i,node_auc.item(), edge_auc.item())
        #model.eval()
        #with torch.no_grad():
        labels = data.y.cpu().numpy()
        auc = roc_auc_score(labels, anomaly_scores.detach().cpu().numpy())
        print(i, f'ROC AUC Score: {auc:.4f}', f'loss: {loss:.4f}')
    
        
    # return total_loss / len(data_loader)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def main():
   
    # load data
    # data = load_mat_with_pe('cora')
    data  = load_mat('cora', path='./data')
    #data  = load_truth('books')
    print('data.x.size(1):',data)
    data = data.to(device)

    model = TAD(in_channels=data.x.size(1),hidden_channels=32,pos_enc_dim=8).to(device)
    # optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
    optimizer = torch.optim.AdamW(model.parameters(), 
                                    lr=0.005,  
                                    weight_decay=1e-5)
    model = train_epoch(model, optimizer,data)


if __name__ == "__main__":
    main()