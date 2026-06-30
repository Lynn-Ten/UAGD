# GT-TAD: Graph Transformer for Unsupervised Graph Outlier Detection

This repository provides the implementation of **GT-TAD**, an unsupervised graph outlier detection model based on graph Transformer encoding and reconstruction-based anomaly scoring. The code also includes several anomaly injection scripts for constructing synthetic structural and attribute outliers on common graph datasets.

## Overview

GT-TAD follows a two-stage experimental workflow:

1. **Inject outliers into clean graph datasets** using one of the provided injection scripts.
2. **Train GT-TAD for unsupervised outlier detection** and evaluate node-level anomaly scores with ROC-AUC.

The main model uses Laplacian positional encoding, Transformer-based node representation learning, and a VAE-style reconstruction module. The final anomaly score of each node is computed from both node attribute reconstruction error and adjacency reconstruction error.

## Repository Structure

```text
.
├── GT-TAD.py              # Main model and training script
├── load_datas.py          # Data loading utilities
├── CB-EDR.py              # Clique-based structural outlier + attribute outlier injection
├── NB-REDR.py             # Neighborhood rewiring + attribute outlier injection
├── MPI.py                 # Multi-pattern anomaly injection
├── analysis.ipynb         # Analysis and visualization notebook
├── raw_dataset/           # Raw graph datasets
├── data_CE/               # Output folder of CB-EDR.py
├── data_NR/               # Output folder of NB-REDR.py
└── data/                  # Default input folder used by GT-TAD.py
```

> Note: the main script imports `load_datas`. If your local file is named `load_data(2).py`, please rename it before running:
>
> ```bash
> mv "load_data(2).py" load_datas.py
> ```

## Requirements

The code requires Python and the following packages:

```text
Python >= 3.8
PyTorch
PyTorch Geometric
NumPy
SciPy
Scikit-learn
NetworkX
PyGOD
Matplotlib
PyYAML
```

A typical installation is:

```bash
conda create -n gttad python=3.9 -y
conda activate gttad

pip install torch numpy scipy scikit-learn networkx matplotlib pyyaml pygod
pip install torch-geometric
```

Please install the PyTorch and PyTorch Geometric versions that match your CUDA environment.

## Dataset Preparation

The injection scripts expect raw datasets to be placed under `raw_dataset/`.

For citation datasets such as Cora, the expected structure is:

```text
raw_dataset/cora/
├── ind.cora.x
├── ind.cora.y
├── ind.cora.tx
├── ind.cora.ty
├── ind.cora.allx
├── ind.cora.ally
├── ind.cora.graph
└── ind.cora.test.index
```

For `.mat` datasets such as BlogCatalog, Flickr, and ACM, the expected structure is:

```text
raw_dataset/BlogCatalog/BlogCatalog.mat
raw_dataset/Flickr/Flickr.mat
raw_dataset/ACM/ACM.mat
```

The `.mat` files should contain at least the following fields:

```text
Network      # adjacency matrix
Attributes   # node attribute matrix
Label        # class labels or anomaly labels, depending on the dataset
```

## Running the Experiments

### Step 1: Inject Outliers

You can choose one of the following injection scripts.

#### 1. CB-EDR Injection

`CB-EDR.py` constructs structural anomalies by forming fully connected node groups and constructs attribute anomalies by replacing selected nodes' attributes with distant node attributes.

Example:

```bash
python CB-EDR.py --dataset cora --seed 1 --m 15 --n 5 --k 50
```

The processed dataset will be saved to:

```text
data_CE/cora.mat
```

#### 2. NB-REDR Injection

`NB-REDR.py` constructs structural anomalies by rewiring selected nodes to nodes from different classes while preserving the original degree. It also constructs attribute anomalies by assigning distant node attributes to selected nodes.

Example:

```bash
python NB-REDR.py --seed 100 --k 20
```

By default, this script processes:

```text
cora, ACM, Flickr, BlogCatalog
```

The processed datasets will be saved to:

```text
data_NR/
```

#### 3. MPI Injection

`MPI.py` provides a multi-pattern injection strategy, including:

- structural edge outliers;
- structural clique outliers;
- local attribute outliers;
- global attribute outliers.

Example:

```bash
python MPI.py \
  --dataset cora \
  --num_structural_edge_outliers 100 \
  --num_structural_clique_outliers 10 \
  --num_attribute_local_outliers 10 \
  --num_attribute_global_outliers 100 \
  --output_dir ./data_MPI \
  --seed 100
```

The processed dataset will be saved to:

```text
data_MPI/cora.mat
```

### Step 2: Run GT-TAD

`GT-TAD.py` is the main entry point. By default, it loads:

```python
load_mat('cora', path='./data')
```

Therefore, before running the model, either copy the generated dataset into `./data/`:

```bash
mkdir -p data
cp data_CE/cora.mat data/cora.mat
python GT-TAD.py
```

or modify the loading path in `GT-TAD.py`, for example:

```python
data = load_mat('cora', path='./data_CE')
```

Then run:

```bash
python GT-TAD.py
```

During training, the script prints the ROC-AUC score and loss at each iteration:

```text
0 ROC AUC Score: 0.xxxx loss: x.xxxx
1 ROC AUC Score: 0.xxxx loss: x.xxxx
...
```

## Model Description

GT-TAD consists of the following components:

1. **Laplacian Positional Encoder**
   - Computes Laplacian eigenvectors as graph positional encodings.

2. **Graph Transformer Encoder**
   - Encodes node attributes and positional information through multi-head self-attention layers.

3. **VAE-style Latent Representation**
   - Produces node-level latent variables through `mu` and `logvar` projections.

4. **Node Attribute Decoder**
   - Reconstructs node attributes from latent representations.

5. **Edge Decoder**
   - Reconstructs the adjacency matrix using a bilinear decoder.

6. **Anomaly Scoring**
   - Computes node anomaly scores by combining node reconstruction error and edge reconstruction error:

```text
score(v) = node_reconstruction_error(v) + edge_reconstruction_error(v)
```

## Data Loading

The repository provides three data loading functions in `load_datas.py`:

```python
load_mat(d_name, path='./NovelStr_datasets/')
```

Loads `.mat` graph datasets with sparse `Network` and `Attributes` fields and returns a PyTorch Geometric `Data` object.

```python
load_truth(name='weibo')
```

Loads real-world graph anomaly detection datasets from PyGOD, such as `weibo`.

```python
load_anmat(d_name, path='./data')
```

Loads dense `.mat` datasets whose label field is named `y`.

## Important Notes

1. **Filename consistency**

   `GT-TAD.py` imports from `load_datas`, so the data loader file should be named `load_datas.py`.

2. **Default path in `GT-TAD.py`**

   The current default input path is `./data`. If you generate data into `data_CE/`, `data_NR/`, or `data_MPI/`, either copy the `.mat` file into `data/` or change the path in `GT-TAD.py`.

3. **Label field for evaluation**

   `GT-TAD.py` evaluates ROC-AUC using `data.y`. Therefore, the loaded label should be a binary anomaly label.

   `CB-EDR.py` and `NB-REDR.py` save the overall anomaly label in the `Label` field. However, `MPI.py` saves class labels in `Label` and stores anomaly labels separately as `str_anomaly_label`, `attr_anomaly_label`, `str_e_anomaly_label`, `str_c_anomaly_label`, `attr_l_anomaly_label`, and `attr_g_anomaly_label`. If you evaluate MPI-generated data, please modify the loader to use the desired anomaly label.

4. **Dense adjacency reconstruction**

   GT-TAD reconstructs a dense `N x N` adjacency matrix. This is convenient for small and medium graphs, but it may require large GPU memory on large-scale graphs.

5. **Running a single dataset with NB-REDR**

   `NB-REDR.py` currently loops over `['cora', 'ACM', 'Flickr', 'BlogCatalog']`. If you only want to process one dataset, modify the `datas` list in the script.

## Example: Full Pipeline on Cora

```bash
# 1. Rename data loader if necessary
mv "load_data(2).py" load_datas.py

# 2. Inject anomalies
python CB-EDR.py --dataset cora --seed 1 --m 15 --n 5 --k 50

# 3. Move generated data to the default input folder
mkdir -p data
cp data_CE/cora.mat data/cora.mat

# 4. Train and evaluate GT-TAD
python GT-TAD.py
```

## Output

The training script reports node-level ROC-AUC and reconstruction loss. A higher ROC-AUC indicates better separation between normal nodes and anomalous nodes.

