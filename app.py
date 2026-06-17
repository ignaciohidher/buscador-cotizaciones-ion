# ─────────────────────────────────────────────────────────────────────────────
# BUSCADOR DE COTIZACIONES · ION Chile
# Autor: Nacho Hidalgo
# Uso: streamlit run app.py
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import pandas as pd
import base64
import plotly.express as px
import os
from difflib import SequenceMatcher

# ── Configuración de la página ────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
LOGO_ISOTIPO = os.path.join(BASE_DIR, "ion_logo2.png")

st.set_page_config(
    page_title="Buscador Cotizaciones · ION Chile",
    page_icon=LOGO_ISOTIPO,
    layout="wide"
)

# ── Estilos CSS corporativos ION ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f0f2f5; }
    [data-testid="stSidebar"] { background-color: #181a1a; }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span { color: #ffffff !important; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #ffffff !important; font-family: 'Inter', sans-serif; font-weight: 500; }
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #2d3030; color: white; border: 1px solid #626666; border-radius: 6px; }
    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background-color: #2d3030; color: white; border: 1px solid #626666; border-radius: 6px; }
    [data-testid="stSidebar"] .stNumberInput > div > div > input {
        background-color: #2d3030; color: white; border: 1px solid #626666; border-radius: 6px; }
    [data-testid="stSidebar"] .stButton button { color: #181a1a !important; font-weight: 600 !important; }
    [data-testid="stSidebar"] button p { color: #181a1a !important; }
    .metric-box { border-radius: 8px; padding: 18px 24px; text-align: center; }
    .metric-box .label { font-size: 11px; font-weight: 500; letter-spacing: 1px; text-transform: uppercase; opacity: .8; margin-bottom: 6px; }
    .metric-box .value { font-size: 26px; font-weight: 700; }
    .metric-dark  { background: #e21b1b; color: white; }
    .metric-blue  { background: #0391d5; color: white; }
    .metric-green { background: #8ec11d; color: white; }
    .header-container {
        background: #181a1a; border-radius: 10px;
        padding: 20px 28px; margin-bottom: 20px;
        display: flex; align-items: center; gap: 24px;
    }
    .header-title { color: #ffffff; font-size: 24px; font-weight: 700; margin: 0; }
    .header-sub   { color: #626666; font-size: 13px; margin: 4px 0 0 0; }
    .stDataFrame { border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
    hr { border: none; border-top: 2px solid #181a1a; margin: 16px 0; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Logos en base64 ───────────────────────────────────────────────────────────
LOGO_PATH    = os.path.join(BASE_DIR, "ion_logo.png")

logo_b64    = base64.b64encode(open(LOGO_PATH, "rb").read()).decode()
isotipo_b64 = base64.b64encode(open(LOGO_ISOTIPO, "rb").read()).decode()

# ── Carga de datos desde Google Sheets ───────────────────────────────────────
SHEET_ID  = "18jORpO5KViHxKG_vmsXXw-df7GMYOCjPLsXGPr4aVXg"
# gviz/tq entrega el CSV con encoding correcto (UTF-8)
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=300)
def load():
    df = pd.read_csv(SHEET_URL, encoding="utf-8")
    # Elimina columnas sin nombre
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df = df.dropna(how="all")
    # Limpia strings
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip().replace("nan", "")
    # Limpia números: quita $, espacios, puntos de miles
    for col in ["Precio Unitario", "Precio Total USD", "Precio Total CLP", "Cantidad"]:
        if col in df.columns:
            df[col] = (df[col].astype(str)
                       .str.replace(r'[\$\s]', '', regex=True)
                       .str.replace('.', '', regex=False)
                       .str.replace(',', '.', regex=False))
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Fecha
    if "Fecha Cotización" in df.columns:
        df["Fecha Cotización"] = pd.to_datetime(
            df["Fecha Cotización"], dayfirst=True, errors="coerce")
    return df

df = load()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="header-container">
    <img src='data:image/png;base64,{isotipo_b64}' height='48'>
    <div>
        <p class="header-title">Buscador de Cotizaciones</p>
        <p class="header-sub">ION Chile &nbsp;·&nbsp; Base de costos de referencia</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Helper: opciones para filtros ────────────────────────────────────────────
def opts(col):
    return ["Todas"] + sorted([v for v in df[col].dropna().unique() if v != ""])

# ── Reset de filtros ──────────────────────────────────────────────────────────
if "reset_count" not in st.session_state:
    st.session_state["reset_count"] = 0

def limpiar_filtros():
    st.session_state["reset_count"] += 1

rc = st.session_state["reset_count"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='text-align:center; padding:16px 0 8px 0'>
        <img src='data:image/png;base64,{isotipo_b64}' height='60'>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 💱 Tipo de Cambio")
    usd_clp = st.number_input("USD → CLP", value=920.0, step=1.0, format="%.0f", key=f"usd_{rc}")
    uf_clp  = st.number_input("UF → CLP",  value=37500.0, step=10.0, format="%.0f", key=f"uf_{rc}")

    st.markdown("### Filtros")
    st.markdown("---")

    search = st.text_input("🔍 Buscar", placeholder="Especificación, proveedor…", key=f"search_{rc}")

    # Filtros en cascada
    cuenta = st.selectbox("Cuenta Contable", opts("Cuenta Contable"), key=f"cuenta_{rc}")
    df_c = df[df["Cuenta Contable"] == cuenta] if cuenta != "Todas" else df

    opts_clas = ["Todas"] + sorted([v for v in df_c["Clasificación"].dropna().unique() if v != ""])
    clas = st.selectbox("Clasificación", opts_clas, key=f"clas_{rc}")
    df_c = df_c[df_c["Clasificación"] == clas] if clas != "Todas" else df_c

    opts_sub = ["Todas"] + sorted([v for v in df_c["Sub-Clasificación"].dropna().unique() if v != ""])
    sub = st.selectbox("Sub-Clasificación", opts_sub, key=f"sub_{rc}")
    df_c = df_c[df_c["Sub-Clasificación"] == sub] if sub != "Todas" else df_c

    opts_desc = ["Todas"] + sorted([v for v in df_c["Descripción"].dropna().unique() if v != ""])
    desc = st.selectbox("Descripción", opts_desc, key=f"desc_{rc}")
    df_c = df_c[df_c["Descripción"] == desc] if desc != "Todas" else df_c

    opts_zona = ["Todas"] + sorted([v for v in df_c["Zona"].dropna().unique() if v != ""])
    zona = st.selectbox("Zona", opts_zona, key=f"zona_{rc}")
    df_c = df_c[df_c["Zona"] == zona] if zona != "Todas" else df_c

    opts_proy = ["Todas"] + sorted([v for v in df_c["Proyecto"].dropna().unique() if v != ""])
    proy = st.selectbox("Proyecto", opts_proy, key=f"proy_{rc}")
    df_c = df_c[df_c["Proyecto"] == proy] if proy != "Todas" else df_c

    opts_prov = ["Todas"] + sorted([v for v in df_c["Proveedor"].dropna().unique() if v != ""])
    prov = st.selectbox("Proveedor", opts_prov, key=f"prov_{rc}")

    st.markdown("---")
    st.button("🔄 Limpiar filtros", on_click=limpiar_filtros)
    st.markdown(
        f"<p style='color:#626666; font-size:11px; text-align:center; margin-top:8px'>"
        f"Actualizado: {pd.Timestamp.now().strftime('%d-%m-%Y %H:%M')}</p>",
        unsafe_allow_html=True
    )

# ── Búsqueda inteligente ──────────────────────────────────────────────────────
def busqueda_inteligente(df, query):
    def busqueda_inteligente(df, query):
    if not query:
        return df
    query_norm = query.lower().strip()
    palabras = query_norm.split()
    mask = df.apply(
        lambda row: all(
            p in " ".join(row.astype(str).values).lower()
            for p in palabras
        ), axis=1
    )
    return df[mask]

# ── Aplicar filtros ───────────────────────────────────────────────────────────
filtered = df.copy()
filtered = busqueda_inteligente(filtered, search)

for col, val in [
    ("Cuenta Contable",   cuenta),
    ("Clasificación",     clas),
    ("Sub-Clasificación", sub),
    ("Descripción",       desc),
    ("Zona",              zona),
    ("Proyecto",          proy),
    ("Proveedor",         prov),
]:
    if val != "Todas":
        filtered = filtered[filtered[col] == val]

# ── Conversión de precios a CLP ───────────────────────────────────────────────
def convertir_a_clp(row, col, usd, uf):
    val = pd.to_numeric(row[col], errors="coerce")
    if pd.isna(val):
        return None
    moneda = str(row.get("Moneda", "")).strip().upper()
    if moneda == "USD":
        return val * usd
    elif moneda == "UF":
        return val * uf
    else:
        return val

filtered = filtered.copy()
filtered["P. Unit. CLP num"] = filtered.apply(
    lambda r: convertir_a_clp(r, "Precio Unitario", usd_clp, uf_clp), axis=1)

def total_en_clp(r, usd, uf):
    clp = convertir_a_clp(r, "Precio Total CLP", usd, uf)
    if clp and not pd.isna(clp) and clp > 0:
        return clp
    usd_val = pd.to_numeric(r.get("Precio Total USD"), errors="coerce")
    if not pd.isna(usd_val) and usd_val > 0:
        return usd_val * usd
    return None

filtered["Total CLP conv. num"] = filtered.apply(
    lambda r: total_en_clp(r, usd_clp, uf_clp), axis=1)

# ── Columna de antigüedad ─────────────────────────────────────────────────────
hoy = pd.Timestamp.now().normalize()

def calcular_antiguedad(fecha):
    try:
        if pd.isna(fecha):
            return None
        return (hoy - pd.Timestamp(fecha)).days
    except:
        return None

def emoji_antiguedad(dias):
    if dias is None:
        return ""
    if dias < 180:
        return f"🟢 {dias}d"
    elif dias < 365:
        return f"🟡 {dias}d"
    else:
        return f"🔴 {dias}d"

filtered["Antigüedad"] = filtered["Fecha Cotización"].apply(calcular_antiguedad)

# ── Métricas ──────────────────────────────────────────────────────────────────
total_usd = pd.to_numeric(filtered["Precio Total USD"], errors="coerce").sum()
total_clp = filtered["Total CLP conv. num"].sum()
n         = len(filtered)

m1, m2, m3 = st.columns(3)
m1.markdown(f'<div class="metric-box metric-dark"><div class="label">Registros</div><div class="value">{n}</div></div>', unsafe_allow_html=True)
m2.markdown(f'<div class="metric-box metric-blue"><div class="label">Total USD</div><div class="value">USD {total_usd:,.0f}</div></div>', unsafe_allow_html=True)
m3.markdown(f'<div class="metric-box metric-green"><div class="label">Total CLP (conv.)</div><div class="value">$ {total_clp:,.0f}</div></div>', unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── Formateo chileno ──────────────────────────────────────────────────────────
def fmt_num(val, decimales=0):
    try:
        if pd.isna(val): return ""
        if decimales == 0:
            return f"{int(round(val)):,}".replace(",", ".")
        else:
            s = f"{val:,.{decimales}f}"
            return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return ""

# ── Tabla de resultados ───────────────────────────────────────────────────────
show_cols = [
    "Cuenta Contable", "Clasificación", "Sub-Clasificación", "Descripción",
    "Especificacion", "Zona", "Proyecto", "Proveedor", "Cantidad", "Unidad",
    "Precio Unitario", "Moneda", "P. Unit. CLP num",
    "Precio Total USD", "Precio Total CLP", "Total CLP conv. num",
    "Fecha Cotización", "Antigüedad", "Observaciones", "Link Archivo"
]
display = filtered[[c for c in show_cols if c in filtered.columns]].copy()

display["Cantidad"]            = filtered["Cantidad"].apply(lambda x: fmt_num(x, 0))
display["Precio Unitario"]     = filtered["Precio Unitario"].apply(lambda x: fmt_num(x, 2))
display["P. Unit. CLP num"]    = filtered["P. Unit. CLP num"].apply(lambda x: fmt_num(x, 0))
display["Precio Total USD"]    = filtered["Precio Total USD"].apply(lambda x: fmt_num(x, 0))
display["Precio Total CLP"]    = filtered["Precio Total CLP"].apply(lambda x: fmt_num(x, 0))
display["Total CLP conv. num"] = filtered["Total CLP conv. num"].apply(lambda x: fmt_num(x, 0))
display["Antigüedad"]          = filtered["Antigüedad"].apply(emoji_antiguedad)
display["Link Archivo"]        = filtered["Link Archivo"].apply(
    lambda val: val if str(val).startswith("http") else "")

display = display.rename(columns={
    "Precio Unitario":     "P. Unit. orig.",
    "P. Unit. CLP num":    "P. Unit. CLP",
    "Precio Total USD":    "Total USD",
    "Precio Total CLP":    "Total CLP orig.",
    "Total CLP conv. num": "Total CLP conv.",
})

st.dataframe(
    display,
    width=1400,
    hide_index=True,
    column_config={
        "P. Unit. orig.":  st.column_config.TextColumn("P. Unit. orig."),
        "P. Unit. CLP":    st.column_config.TextColumn("P. Unit. CLP"),
        "Total USD":       st.column_config.TextColumn("Total USD"),
        "Total CLP orig.": st.column_config.TextColumn("Total CLP orig."),
        "Total CLP conv.": st.column_config.TextColumn("Total CLP conv."),
        "Cantidad":        st.column_config.TextColumn("Cantidad"),
        "Antigüedad":      st.column_config.TextColumn("Antigüedad", help="🟢 < 6 meses  🟡 6-12 meses  🔴 > 1 año"),
        "Fecha Cotización":st.column_config.DateColumn("Fecha", format="DD-MM-YYYY"),
        "Link Archivo":    st.column_config.LinkColumn("Archivo", display_text="📄 Ver PDF"),
        "Observaciones":   st.column_config.TextColumn("Observaciones", width="medium"),
    }
)

# ── Análisis gráfico ──────────────────────────────────────────────────────────
hay_filtro = any([
    search,
    cuenta != "Todas", clas != "Todas", sub  != "Todas", desc != "Todas",
    zona   != "Todas", proy  != "Todas", prov != "Todas"
])

if hay_filtro and n > 0:
    st.markdown("### 📊 Análisis")

    tipo_grafico = st.radio(
        "Selecciona el análisis:",
        ["Precio Unitario por Especificación", "Comparador de Proveedores", "Evolución de Precios en el Tiempo"],
        horizontal=True
    )

    if tipo_grafico == "Precio Unitario por Especificación":
        chart_data = filtered[["Especificacion", "P. Unit. CLP num"]].dropna()
        chart_data = chart_data[chart_data["P. Unit. CLP num"] > 0].copy()
        chart_data["Especificacion"] = chart_data["Especificacion"].str[:40]
        chart_data = chart_data.sort_values("P. Unit. CLP num", ascending=True).tail(15)

        fig = px.bar(
            chart_data,
            x="P. Unit. CLP num", y="Especificacion",
            orientation="h",
            color_discrete_sequence=["#0391d5"],
            text=chart_data["P. Unit. CLP num"].apply(lambda x: fmt_num(x, 0))
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_family="Inter", font_color="#181a1a",
            xaxis_title="Precio Unitario (CLP)", yaxis_title="",
            margin=dict(l=20, r=100, t=20, b=20), height=420
        )
        st.plotly_chart(fig, use_container_width=True)

    elif tipo_grafico == "Comparador de Proveedores":
        comp = filtered[["Descripción", "Proveedor", "P. Unit. CLP num"]].dropna()
        comp = comp[comp["P. Unit. CLP num"] > 0].copy()

        if comp.empty:
            st.info("No hay datos suficientes para comparar proveedores.")
        else:
            comp = comp.groupby(["Descripción", "Proveedor"], as_index=False)["P. Unit. CLP num"].mean()
            comp = comp.sort_values("P. Unit. CLP num", ascending=True)

            proveedores = comp["Proveedor"].unique()
            colores = ["#0391d5","#e21b1b","#8ec11d","#f5a623","#9b59b6","#1abc9c","#e67e22","#34495e"]
            color_map = {p: colores[i % len(colores)] for i, p in enumerate(proveedores)}

            fig = px.bar(
                comp,
                x="P. Unit. CLP num", y="Descripción",
                color="Proveedor",
                orientation="h",
                color_discrete_map=color_map,
                text=comp["P. Unit. CLP num"].apply(lambda x: fmt_num(x, 0)),
                barmode="group"
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="Inter", font_color="#181a1a",
                xaxis_title="Precio Unitario Promedio (CLP)", yaxis_title="",
                legend_title="Proveedor",
                margin=dict(l=20, r=120, t=20, b=20),
                height=max(350, len(comp) * 35)
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("💡 Tip: filtra por Descripción o Sub-Clasificación para comparar ítems similares.")

    elif tipo_grafico == "Evolución de Precios en el Tiempo":
        evol = filtered[["Fecha Cotización", "Especificacion", "P. Unit. CLP num"]].dropna()
        evol["Fecha Cotización"] = pd.to_datetime(evol["Fecha Cotización"], errors="coerce")
        evol = evol[evol["P. Unit. CLP num"] > 0].copy()
        evol = evol.dropna(subset=["Fecha Cotización"])
        evol = evol.sort_values("Fecha Cotización")
        evol["Especificacion"] = evol["Especificacion"].str[:35]

        if evol.empty:
            st.info("No hay fechas disponibles para los registros filtrados.")
        elif len(evol["Especificacion"].unique()) > 10:
            st.info("💡 Demasiados productos. Filtra por Descripción para ver la evolución.")
        else:
            fig = px.bar(
                evol,
                x="Fecha Cotización", y="P. Unit. CLP num",
                color="Especificacion",
                barmode="group",
                text=evol["P. Unit. CLP num"].apply(lambda x: fmt_num(x, 0)),
                color_discrete_sequence=["#0391d5","#e21b1b","#8ec11d","#f5a623","#9b59b6","#1abc9c"]
            )
            fig.update_traces(textposition="outside", textangle=0)
            fig.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font_family="Inter", font_color="#181a1a",
                xaxis_title="Fecha", yaxis_title="Precio Unitario (CLP)",
                legend_title="Especificación",
                margin=dict(l=20, r=20, t=30, b=20), height=450
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("💡 Tip: filtra por Descripción para ver la evolución de precios en el tiempo.")

# ── Exportar a CSV ────────────────────────────────────────────────────────────
_, _, col_btn = st.columns([4, 4, 2])
with col_btn:
    csv = display.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️  Exportar a CSV", csv, "cotizaciones_filtradas.csv", "text/csv")
