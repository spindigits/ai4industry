import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
        /* Amélioration des titres */
        h1 {
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(120deg, #ef4444, #b91c1c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            padding-bottom: 1rem;
        }

        h2 {
            font-weight: 600;
            padding-top: 1rem;
            border-bottom: 2px solid #ef4444;
            padding-bottom: 0.5rem;
        }

        h3 {
            font-weight: 600;
            color: #ef4444;
            margin-top: 1.5rem;
        }

        /* Amélioration des cartes métriques */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 700;
            color: #ef4444;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.9rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Amélioration des expanders */
        .streamlit-expanderHeader {
            font-weight: 600;
            background-color: rgba(239, 68, 68, 0.1);
            border-radius: 8px;
            padding: 0.5rem;
        }

        /* Amélioration des inputs */
        .stTextInput input {
            border-radius: 8px;
            border: 2px solid #ef4444;
            padding: 0.75rem;
            font-size: 1rem;
        }

        .stTextInput input:focus {
            border-color: #b91c1c;
            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
        }

        /* Amélioration des boutons */
        .stButton button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1.5rem;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }

        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        }

        /* Amélioration des tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(239, 68, 68, 0.05);
            padding: 0.5rem;
            border-radius: 8px;
        }

        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background-color: transparent;
            border-radius: 8px;
            font-weight: 600;
            padding: 0 1.5rem;
        }

        .stTabs [aria-selected="true"] {
            background-color: #ef4444;
            color: #000000 !important;
            font-weight: 800 !important;
        }

        /* Amélioration des messages info/success */
        .stAlert {
            border-radius: 8px;
            border-left: 4px solid #ef4444;
            padding: 1rem;
        }

        /* Amélioration du spinner */
        .stSpinner > div {
            border-top-color: #ef4444;
        }

        /* Amélioration de la sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(239, 68, 68, 0.05) 0%, transparent 100%);
        }

        /* Amélioration des dividers */
        hr {
            margin: 2rem 0;
            border: none;
            height: 2px;
            background: linear-gradient(90deg, transparent, #ef4444, transparent);
        }

        /* Amélioration des dataframes */
        .dataframe {
            border-radius: 8px;
            overflow: hidden;
        }

        /* Animation de fade-in pour le contenu */
        .element-container {
            animation: fadeIn 0.5s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Style des badges personnalisés */
        .badge {
            display: inline-block;
            padding: 0.35rem 0.65rem;
            font-size: 0.85rem;
            font-weight: 600;
            line-height: 1;
            border-radius: 6px;
            margin: 0.25rem;
        }

        .badge-success {
            background-color: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid #ef4444;
        }

        .badge-info {
            background-color: rgba(59, 130, 246, 0.2);
            color: #3b82f6;
            border: 1px solid #3b82f6;
        }
        </style>
    """, unsafe_allow_html=True)
