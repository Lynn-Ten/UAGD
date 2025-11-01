import numpy as np
import scipy.sparse as sp
import random
import scipy.io as sio
import argparse
import networkx as nx
from sklearn import preprocessing
import pickle as pkl
from scipy.stats import multivariate_normal
import os

def dense_to_sparse(dense_matrix):
    shape = dense_matrix.shape
    row = []
    col = []
    data = []
    for i, r in enumerate(dense_matrix):
        for j in np.where(r > 0)[0]:
            row.append(i)
            col.append(j)
            data.append(dense_matrix[i, j])
    return sp.coo_matrix((data, (row, col)), shape=shape).tocsc()

def parse_index_file(filename):
    index = []
    for line in open(filename):
        index.append(int(line.strip()))
    return index

def load_citation_datadet(dataset_str):
    names = ['x', 'y', 'tx', 'ty', 'allx', 'ally', 'graph']
    objects = []
    for i in range(len(names)):
        with open(f"raw_dataset/{dataset_str}/ind.{dataset_str}.{names[i]}", 'rb') as f:
            objects.append(pkl.load(f, encoding='latin1'))
    x, y, tx, ty, allx, ally, graph = tuple(objects)
    test_idx_reorder = parse_index_file(f"raw_dataset/{dataset_str}/ind.{dataset_str}.test.index")
    test_idx_range = np.sort(test_idx_reorder)

    if dataset_str == 'citeseer':
        test_idx_range_full = range(min(test_idx_reorder), max(test_idx_reorder) + 1)
        tx_extended = sp.lil_matrix((len(test_idx_range_full), x.shape[1]))
        tx_extended[test_idx_range - min(test_idx_range), :] = tx
        tx = tx_extended
        ty_extended = np.zeros((len(test_idx_range_full), y.shape[1]))
        ty_extended[test_idx_range - min(test_idx_range), :] = ty
        ty = ty_extended

    features = sp.vstack((allx, tx)).tolil()
    features[test_idx_reorder, :] = features[test_idx_range, :]
    adj = nx.adjacency_matrix(nx.from_dict_of_lists(graph))
    labels = np.vstack((ally, ty))
    labels[test_idx_reorder, :] = labels[test_idx_range, :]

    adj_dense = np.array(adj.todense(), dtype=np.float64)
    attribute_dense = np.array(features.todense(), dtype=np.float64)
    cat_labels = np.array(np.argmax(labels, axis=1).reshape(-1, 1), dtype=np.uint8)

    return attribute_dense, adj_dense, cat_labels

def inject_structural_edge_outliers(adj_dense, cat_labels, num_outliers=50):
    num_nodes = adj_dense.shape[0]
    outlier_nodes = np.random.choice(num_nodes, num_outliers, replace=False)
    
    for node_id in outlier_nodes:
        cat_y = cat_labels[node_id]
        all_other_label_nodes = (cat_labels != cat_y).nonzero()[0]
        if len(all_other_label_nodes) == 0:
            print(f"Node {node_id} has no other label nodes to connect to.")
            continue  
        ori_deg = int(np.sum(adj_dense[node_id]))
        
        if ori_deg == 0:
            print(f"Node {node_id} has no original edges.")
            continue
        
        new_neighbors = np.random.choice(all_other_label_nodes, ori_deg, replace=False)
        
        adj_dense[node_id] = 0
        adj_dense[node_id, new_neighbors] = 1
        adj_dense[new_neighbors, node_id] = adj_dense[node_id, new_neighbors].copy()
    
    
    str_e_y = np.zeros(num_nodes, dtype=int)
    str_e_y[outlier_nodes] = 1  
    
    return adj_dense, str_e_y

def inject_structural_clique_outliers(adj_dense, num_outliers=5, clique_size_range=(5, 10)):
    num_nodes = adj_dense.shape[0]
    str_c_y = np.zeros(num_nodes, dtype=int)
    
    for _ in range(num_outliers):  
        clique_size = np.random.randint(clique_size_range[0], clique_size_range[1] + 1)
        
        clique_nodes = np.random.choice(num_nodes, clique_size, replace=False)
        
        for i in clique_nodes:
            for j in clique_nodes:
                if i != j:  
                    adj_dense[i, j] = 1
                    adj_dense[j, i] = 1
        
        str_c_y[clique_nodes] = 1 
    
    return adj_dense, str_c_y

def inject_attribute_local_outliers(attribute_dense, adj_dense, num_outliers=50):
    num_nodes = attribute_dense.shape[0]
    num_features = attribute_dense.shape[1]
    outlier_nodes = np.random.choice(num_nodes, num_outliers, replace=False)
    attr_l_y = np.zeros(num_nodes, dtype=int)  
    
    for node in outlier_nodes:
        neighbors = np.where(adj_dense[node] > 0)[0]
        if len(neighbors) == 0:
            print(f"Node {node} has no neighbors.")
            continue  
        neighbor_features = attribute_dense[neighbors]
        mean = np.mean(neighbor_features, axis=0)
        cov = np.cov(neighbor_features, rowvar=False)
        
        new_features = multivariate_normal.rvs(mean, cov * 3, size=1)
        attribute_dense[node] = new_features
        
        attr_l_y[node] = 1  
    
    return attribute_dense, attr_l_y

import numpy as np

def inject_attribute_global_outliers(attribute_dense, num_outliers=50, change_ratio=1):
    num_nodes = attribute_dense.shape[0]
    num_features = attribute_dense.shape[1]
    outlier_nodes = np.random.choice(num_nodes, num_outliers, replace=False)
    attr_g_y = np.zeros(num_nodes, dtype=int)  
    
    global_min = np.min(attribute_dense, axis=0)  
    global_max = np.max(attribute_dense, axis=0)  
    
    for node in outlier_nodes:
        num_changes = int(change_ratio * num_features)  
        change_dims = np.random.choice(num_features, num_changes, replace=False)  
        
        new_features = attribute_dense[node].copy()  
        for k in change_dims:
            new_features[k] = np.random.choice([global_min[k] * 1.01, global_max[k] * 1.01])
        
        attribute_dense[node] = new_features
        
        attr_g_y[node] = 1  
    
    return attribute_dense, attr_g_y

def save_injected_data(attribute_dense, adj_dense, cat_labels, str_y, str_e_y, str_c_y, attr_y, attr_l_y, attr_g_y, dataset_name, output_dir='./data_MPI/'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    sio.savemat(f'{output_dir}/{dataset_name}.mat', {
        'Attributes': attribute_dense,
        'Network': adj_dense,
        'Label': cat_labels,
        'str_anomaly_label': str_y,
        'str_e_anomaly_label': str_e_y,
        'str_c_anomaly_label': str_c_y,
        'attr_anomaly_label': attr_y,
        'attr_l_anomaly_label': attr_l_y,
        'attr_g_anomaly_label': attr_g_y
    })
    print(f"Injected data saved to {output_dir}/{dataset_name}_injected.mat")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, default='cora', help='Dataset name')
    parser.add_argument('--num_structural_edge_outliers', type=int, default=100, help='Number of structural edge outliers to inject')
    parser.add_argument('--num_structural_clique_outliers', type=int, default=10, help='Number of structural clique outliers to inject')
    parser.add_argument('--num_attribute_local_outliers', type=int, default=10, help='Number of attribute local outliers to inject')
    parser.add_argument('--num_attribute_global_outliers', type=int, default=100, help='Number of attribute global outliers to inject')
    parser.add_argument('--output_dir', type=str, default='./injected_data', help='Output directory for saving injected data')
    parser.add_argument('--seed', type=int, default=100)  #random seed
    args = parser.parse_args()
    seed = args.seed
    
    # 加载数据
    if args.dataset in ['BlogCatalog', 'Flickr']:
        print('Random seed: {:d}. \n'.format(seed))
        np.random.seed(seed)
        random.seed(seed)
        data = sio.loadmat(f'./raw_dataset/{args.dataset}/{args.dataset}.mat')
        #print(data.keys())    
        attribute_dense = np.array(data['Attributes'].todense())
        adj_dense = np.array(data['Network'].todense())
        cat_labels = data['Label'].flatten()
        #print(f"Attributes shape: {attribute_dense.shape}")  # 应为 (num_nodes, num_features)
        #print(f"Network shape: {adj_dense.shape}")           # 应为 (num_nodes, num_nodes)
        #print(f"Labels shape: {cat_labels.shape}")           # 应为 (num_nodes,)
        #print("Unique labels:", np.unique(cat_labels))
    elif args.dataset in ['cora']:
        attribute_dense, adj_dense, cat_labels = load_citation_datadet(args.dataset)
        #print(f"Attributes shape: {attribute_dense.shape}")  # 应为 (num_nodes, num_features)
        #print(f"Network shape: {adj_dense.shape}")           # 应为 (num_nodes, num_nodes)
        #print(f"Labels shape: {cat_labels.shape}") 
    else:
        raise ValueError(f"Unsupported dataset: {args.dataset}")
    
    num_nodes = adj_dense.shape[0]
    str_y = np.zeros(num_nodes, dtype=int)  
    str_e_y = np.zeros(num_nodes, dtype=int)  
    str_c_y = np.zeros(num_nodes, dtype=int)  
    attr_y = np.zeros(num_nodes, dtype=int)  
    attr_l_y = np.zeros(num_nodes, dtype=int)  
    attr_g_y = np.zeros(num_nodes, dtype=int)  
    #print("Injecting anomalies...")
    
    adj_dense, str_e_y = inject_structural_edge_outliers(adj_dense, cat_labels, num_outliers=args.num_structural_edge_outliers)
    str_y = np.logical_or(str_y, str_e_y)  
    #print("Injecting structural clique anomalies...")

    adj_dense, str_c_y = inject_structural_clique_outliers(adj_dense, num_outliers=args.num_structural_clique_outliers)
    str_y = np.logical_or(str_y, str_c_y)  
    #print("Injecting attribute local outliers...")
    
    attribute_dense, attr_l_y = inject_attribute_local_outliers(attribute_dense, adj_dense, num_outliers=args.num_attribute_local_outliers)
    attr_y = np.logical_or(attr_y, attr_l_y)  
    #print("Injecting attribute global outliers...")
    
    attribute_dense, attr_g_y = inject_attribute_global_outliers(attribute_dense, num_outliers=args.num_attribute_global_outliers)
    attr_y = np.logical_or(attr_y, attr_g_y)  
    #print("Anomalies injected ending.")
    
    save_injected_data(
        attribute_dense, adj_dense, cat_labels,
        str_y, str_e_y, str_c_y, attr_y, attr_l_y, attr_g_y,
        args.dataset, output_dir=args.output_dir
    )

if __name__ == "__main__":
    main()