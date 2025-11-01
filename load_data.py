import yaml
import torch
from torch_geometric.data import Data
import scipy.io as sio
from pygod.utils import load_data as ld
from utils.posenc_stats import compute_posenc_stats
from utils.transforms import concat_x_and_pos
from torch_geometric.utils import to_dense_adj
from torch_geometric import utils

def load_mat(d_name,path='./NovelStr_datasets/'):
    """
    Load data from a .mat file and apply position encoding and transformations based on cfg.
    """
    data = sio.loadmat(f'{path}/{d_name}.mat')
    adj = torch.FloatTensor(data['Network'].toarray())
    attr = torch.FloatTensor(data['Attributes'].toarray())
    label = torch.LongTensor(data['Label'].reshape(-1))

    edge_index = torch.nonzero(adj).t().contiguous()
    pyg_data = Data(x=attr, edge_index=edge_index, y=label)
    
    return pyg_data


def load_truth(name='weibo'):
    """
    Load Weibo data and apply position encoding and transformations based on cfg.
    """
    data = ld(name=name)
    data.str_y = data.attr_y = data.y
    adj = data.adj = to_dense_adj(data.edge_index)[0]
    edge_index = torch.nonzero(adj).t().contiguous()
    pyg_data = Data(x=data.x, edge_index=edge_index, y=data.y)
    
    return pyg_data

def load_anmat(d_name, path='./data'):
    # 加载 .mat 文件
    data = sio.loadmat(f'{path}/{d_name}.mat')
    
    # 提取数据并转换为 PyTorch 张量
    adj = torch.FloatTensor(data['Network'])  # 邻接矩阵
    attr = torch.FloatTensor(data['Attributes'])  # 特征矩阵
    label = torch.LongTensor(data['y'].reshape(-1))  # 节点标签
    #str_label = torch.LongTensor(data['str_anomaly_label'].reshape(-1))  # 结构异常标签
    #str_c_y = torch.LongTensor(data['str_c_anomaly_label'].reshape(-1))  # Clique 异常标签
    #attr_l_y = torch.LongTensor(data['attr_l_anomaly_label'].reshape(-1))  # 属性局部异常标签
    #attr_g_y = torch.LongTensor(data['attr_g_anomaly_label'].reshape(-1))  # 属性全局异常标签
    edge_index = utils.dense_to_sparse(adj)[0]

    pygData = Data(x=attr, edge_index=edge_index, y=label)
    return pygData
