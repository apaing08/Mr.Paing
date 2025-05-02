import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

def render_table(table_data):
    if isinstance(table_data, list) and all(isinstance(row, list) for row in table_data):
        df = pd.DataFrame(table_data[1:], columns=table_data[0])
        st.table(df)


def render_line_graph(graph_data):
    try:
        x = graph_data.get("x", [])
        y = graph_data.get("y", [])
        label = graph_data.get("label", "")

        fig, ax = plt.subplots()
        ax.plot(x, y, marker="o", label=label)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title(label or "Line Graph")
        ax.grid(True)
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error rendering graph: {e}")