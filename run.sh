#!/bin/bash
# Explicitly source Conda's setup so 'conda activate' works in scripts
source ~/anaconda3/etc/profile.d/conda.sh
conda activate base
streamlit run main.py
