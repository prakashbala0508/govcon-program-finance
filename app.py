app_code = '''
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

st.set_page_config(
    page_title="GovCon Program Financial Management Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #003865 0%, #005a9e 100%);
        padding: 24px 32px; border-radius: 8px;
        margin-bottom: 24px;
    }
    .main-header h1 { color: white; font-size: 24px; margin: 0; font-weight: 600; }
    .main-header p  { color: #b3d1f0; font-size: 13px; margin: 6px 0 0; }
    .kpi-card {
        background: white; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 16px 20px;
        border-left: 4px solid #003865;
    }
    .kpi-label { font-size: 11px; color: #64748b; font-weight: 600;
                 text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-value { font-size: 24px; color: #1a1a2e; font-weight: 700; margin: 4px 0; }
    .kpi-sub   { font-size: 12px; color: #64748b; }
    .section-header {
        font-size: 14px; font-weight: 600; color: #003865;
        border-bottom: 2px solid #003865;
        padding-bottom: 6px; margin: 24px 0 16px;
    }
    div[data-testid="stSidebar"] { background: #f8fafc; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    base = os.path.join(os.path.dirname(__file__), "data")
    return {
        "contracts":  pd.read_csv(os.path.join(base, "contracts.csv")),
        "actuals":    pd.read_csv(os.path.join(base, "monthly_actuals.csv")),
        "eac":        pd.read_csv(os.path.join(base, "eac_data.csv")),
        "rates":      pd.read_csv(os.path.join(base, "indirect_rates.csv")),
        "labor":      pd.read_csv(os.path.join(base, "labor_data.csv")),
        "funding":    pd.read_csv(os.path.join(base, "funding_tracker.csv")),
    }

d = load_data()
contracts, actuals, eac_df, rates, labor, funding = (
    d["contracts"], d["actuals"], d["eac"], d["rates"], d["labor"], d["funding"]
)

with st.sidebar:
    st.markdown("### Navigation")
    module = st.radio("Select Module", [
        "Portfolio Overview",
        "EAC Engine",
        "Indirect Rate Modeler",
        "Variance Analysis",
        "Funding and Burn Rate",
        "Data Sources and Methodology",
    ])
    st.markdown("---")
    st.markdown(
        "<small style='color:#94a3b8'>"
        "<b>GovCon Program Financial Management Suite</b><br><br>"
        "Built by Prakash Balasubramanian<br><br>"
        "Contract data: USASpending.gov<br>"
        "Actuals: Modeled synthetic data<br>"
        "Rates: DCAA benchmarks</small>",
        unsafe_allow_html=True
    )

st.markdown("""
<div class="main-header">
  <h1>GovCon Program Financial Management Suite</h1>
  <p>Program Finance | EAC Modeling | Variance Analysis | Indirect Rate Impact | Burn Rate Tracking
  | Contract data sourced from USASpending.gov | Actuals are modeled projections</p>
</div>
""", unsafe_allow_html=True)

# ===================================================
# MODULE 1 - PORTFOLIO OVERVIEW
# ===================================================
if module == "Portfolio Overview":
    st.markdown("<div class='section-header'>Portfolio Summary</div>", unsafe_allow_html=True)

    total_ceiling = contracts["contract_ceiling"].sum()
    total_funded  = contracts["funded_ceiling"].sum()
    total_spent   = actuals["actual_total"].sum()
    active        = contracts[contracts["status"] == "Active"].shape[0]

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value, sub in zip(
        [c1, c2, c3, c4],
        ["Total Portfolio Value", "Total Funded Ceiling", "Costs Incurred YTD", "Active Contracts"],
        [f"${total_ceiling/1e6:.2f}M", f"${total_funded/1e6:.2f}M", f"${total_spent/1e6:.2f}M", str(active)],
        [f"{len(contracts)} contracts", f"{total_funded/total_ceiling*100:.0f}% of ceiling",
         "Actuals across portfolio", f"of {len(contracts)} total"]
    ):
        col.markdown(f"""<div class='kpi-card'>
            <div class='kpi-label'>{label}</div>
            <div class='kpi-value'>{value}</div>
            <div class='kpi-sub'>{sub}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>Contract Register</div>", unsafe_allow_html=True)
    st.caption("Contract numbers, agencies, and award values are real federal procurement records from USASpending.gov.")

    merged = contracts.merge(eac_df, on="contract_id")
    merged["Risk Flag"] = merged["overrun_flag"].map({True: "Overrun Risk", False: "On Track"})
    merged["Utilization"] = (merged["actual_cost_work_performed"] / merged["budget_at_completion"] * 100).round(1).astype(str) + "%"
    merged["EAC vs BAC"] = merged.apply(
        lambda r: f"${r['estimate_at_completion']/1e6:.2f}M vs ${r['budget_at_completion']/1e6:.2f}M", axis=1
    )
    display = merged[[
        "usaspending_award_id", "contract_name", "agency", "contract_type", "status", "Utilization", "EAC vs BAC", "Risk Flag"
    ]].rename(columns={
        "usaspending_award_id": "Award ID (USASpending)",
        "contract_name": "Contract",
        "agency": "Agency",
        "contract_type": "Type",
        "status": "Status",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("<div class='section-header'>Cost Mix by Contract (YTD)</div>", unsafe_allow_html=True)
    cost = actuals.groupby("contract_id")[["actual_labor", "actual_odc", "actual_subcontractor"]].sum().reset_index()
    cost = cost.merge(contracts[["contract_id", "contract_name"]], on="contract_id")

    fig = go.Figure()
    for col_name, label, color in zip(
        ["actual_labor", "actual_odc", "actual_subcontractor"],
        ["Direct Labor", "ODC", "Subcontractor"],
        ["#003865", "#005a9e", "#7fb3d3"]
    ):
        fig.add_trace(go.Bar(name=label, x=cost["contract_name"], y=cost[col_name], marker_color=color))
    fig.update_layout(
        barmode="stack", height=340, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20, b=60, l=40, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f1f5f9"),
        xaxis=dict(tickfont=dict(size=10))
    )
    st.plotly_chart(fig, use_container_width=True)

# ===================================================
# MODULE 2 - EAC ENGINE
# ===================================================
elif module == "EAC Engine":
    st.markdown("<div class='section-header'>Estimate at Completion (EAC) Analysis</div>", unsafe_allow_html=True)
    st.caption(
        "EAC projects the total cost of each contract at completion based on actual performance to date. "
        "A positive Variance at Completion (VAC) means under budget (favorable). "
        "A negative VAC signals a cost overrun. "
        "EAC projections are synthetic models calibrated to real USASpending.gov award values."
    )

    merged = eac_df.merge(
        contracts[["contract_id", "contract_name", "contract_type", "base_fee_pct", "usaspending_award_id"]],
        on="contract_id"
    )
    merged["fee_earned"] = merged["budget_at_completion"] * merged["base_fee_pct"]
    merged["fee_at_risk"] = merged.apply(
        lambda r: max(0, r["estimate_at_completion"] - r["budget_at_completion"]) * r["base_fee_pct"], axis=1
    )

    for _, row in merged.iterrows():
        is_overrun = row["overrun_flag"]
        risk_label = "OVERRUN RISK" if is_overrun else "ON TRACK"
        vac = row["variance_at_completion"]
        vac_fmt = f"-${abs(vac)/1e3:.0f}K Unfavorable" if vac < 0 else f"+${vac/1e3:.0f}K Favorable"

        with st.expander(f"{row['contract_name']} | {row['contract_type']} | {risk_label}", expanded=True):
            st.caption(f"Award ID: {row['usaspending_award_id']} | Source: USASpending.gov")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Budget at Completion (BAC)", f"${row['budget_at_completion']/1e6:.2f}M")
            c2.metric("Estimate at Completion (EAC)", f"${row['estimate_at_completion']/1e6:.2f}M")
            c3.metric("Variance at Completion (VAC)", vac_fmt)
            c4.metric("Percent Complete", f"{row['pct_complete']*100:.0f}%")

            risk_color = "#dc2626" if is_overrun else "#16a34a"
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["BAC (Budget)", "ACWP (Actual)", "EAC (Projected)"],
                y=[row["budget_at_completion"], row["actual_cost_work_performed"], row["estimate_at_completion"]],
                marker_color=["#003865", "#005a9e", risk_color],
                width=0.5
            ))
            fig.add_hline(
                y=row["budget_at_completion"], line_dash="dot",
                line_color="#dc2626", annotation_text="Budget Ceiling",
                annotation_position="top right"
            )
            fig.update_layout(
                height=260, plot_bgcolor="white", paper_bgcolor="white",
                margin=dict(t=20, b=10, l=40, r=20),
                yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f1f5f9"),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

            if is_overrun:
                commentary = (
                    f"Contract is {row['pct_complete']*100:.0f}% complete. "
                    f"EAC of ${row['estimate_at_completion']/1e6:.2f}M against a BAC of "
                    f"${row['budget_at_completion']/1e6:.2f}M yields a VAC of {vac_fmt}. "
                    f"Action required: Contract is projecting a cost overrun. "
                    f"Recommend immediate review of labor burn rate by category and validation of "
                    f"subcontractor invoices against deliverables. Corrective action plan due before next EAC cycle."
                )
            else:
                commentary = (
                    f"Contract is {row['pct_complete']*100:.0f}% complete. "
                    f"EAC of ${row['estimate_at_completion']/1e6:.2f}M against a BAC of "
                    f"${row['budget_at_completion']/1e6:.2f}M yields a VAC of {vac_fmt}. "
                    f"Contract is tracking within budget. Continue monitoring monthly actuals against EAC assumptions. "
                    f"Fee earned: ${row['fee_earned']/1e3:.0f}K. Fee at risk: ${row['fee_at_risk']/1e3:.0f}K."
                )
            st.markdown(f"**Analyst Commentary:** {commentary}")

# ===================================================
# MODULE 3 - INDIRECT RATE MODELER
# ===================================================
elif module == "Indirect Rate Modeler":
    st.markdown("<div class='section-header'>Indirect Rate Impact Modeler</div>", unsafe_allow_html=True)
    st.caption(
        "Indirect rates (Fringe, Overhead, G&A) are applied on top of direct labor costs. "
        "When provisional rates change due to DCAA audit adjustments, every contract's fully burdened cost and margin shifts. "
        "Rates are benchmarked to DCAA published ranges for NAICS 541 professional services firms."
    )

    col_ctrl, col_res = st.columns([1, 2])
    with col_ctrl:
        st.markdown("**Adjust Provisional Rates**")
        fringe   = st.slider("Fringe Rate (%)",   20, 45, 32, help="Benefits and payroll taxes applied to direct labor") / 100
        overhead = st.slider("Overhead Rate (%)", 30, 60, 45, help="Indirect labor and facilities applied to direct labor") / 100
        ga       = st.slider("G&A Rate (%)",       8, 20, 12, help="General and Administrative applied to total cost input") / 100
        st.markdown("---")
        st.markdown("**DCAA Benchmark Ranges**")
        st.markdown("Fringe: 29% to 36%")
        st.markdown("Overhead: 41% to 51%")
        st.markdown("G&A: 10% to 15%")
        st.caption("Source: DCAA provisional rate guidance for NAICS 541")

    dl = labor.groupby("contract_id").apply(
        lambda x: (x["hours_actual"] * x["bill_rate"]).sum()
    ).reset_index(name="direct_labor")
    dl = dl.merge(contracts[["contract_id", "contract_name", "base_fee_pct"]], on="contract_id")
    dl["fringe"]       = dl["direct_labor"] * fringe
    dl["overhead"]     = dl["direct_labor"] * overhead
    dl["total_direct"] = dl["direct_labor"] + dl["fringe"] + dl["overhead"]
    dl["ga"]           = dl["total_direct"] * ga
    dl["total_cost"]   = dl["total_direct"] + dl["ga"]
    dl["fee"]          = dl["total_cost"] * dl["base_fee_pct"]
    dl["total_billed"] = dl["total_cost"] + dl["fee"]

    with col_res:
        st.markdown("**Fully Burdened Cost - Rate Stack**")
        disp = dl[["contract_name", "direct_labor", "fringe", "overhead", "ga", "total_cost", "fee", "total_billed"]].copy()
        disp.columns = ["Contract", "Direct Labor", "Fringe", "Overhead", "G&A", "Total Cost", "Fee", "Total Billed"]
        for c in disp.columns[1:]:
            disp[c] = disp[c].apply(lambda x: f"${x:,.0f}")
        st.dataframe(disp, use_container_width=True, hide_index=True)

        fig = go.Figure()
        for col_name, label, color in zip(
            ["direct_labor", "fringe", "overhead", "ga", "fee"],
            ["Direct Labor", "Fringe", "Overhead", "G&A", "Fee"],
            ["#003865", "#005a9e", "#1e7fc2", "#7fb3d3", "#b3d1f0"]
        ):
            fig.add_trace(go.Bar(name=label, x=dl["contract_name"], y=dl[col_name], marker_color=color))
        fig.update_layout(
            barmode="stack", height=300, plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=10, b=60, l=40, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f1f5f9"),
        )
        st.plotly_chart(fig, use_container_width=True)

    total_billed = dl["total_billed"].sum()
    ga_impact    = dl["total_direct"].sum() * 0.01
    st.info(
        f"Portfolio Impact: At current rates (Fringe: {fringe*100:.0f}%, Overhead: {overhead*100:.0f}%, G&A: {ga*100:.0f}%), "
        f"total fully burdened portfolio cost is ${total_billed/1e6:.2f}M. "
        f"A 1% increase in G&A alone adds ${ga_impact/1e3:.0f}K across the portfolio. "
        f"Recommend flagging any rate variance above 2% to program managers immediately."
    )

# ===================================================
# MODULE 4 - VARIANCE ANALYSIS
# ===================================================
elif module == "Variance Analysis":
    st.markdown("<div class='section-header'>Monthly Variance Analysis - Actuals vs. Budget</div>", unsafe_allow_html=True)
    st.caption(
        "Variance analysis compares budgeted spend against actual costs each period. "
        "Favorable variance means under budget. Unfavorable means over budget. "
        "Monthly actuals are synthetic projections calibrated to real USASpending.gov award values."
    )

    col_filter, _ = st.columns([1, 3])
    with col_filter:
        options = ["All Contracts"] + contracts["contract_name"].tolist()
        selected = st.selectbox("Filter by Contract", options)

    if selected == "All Contracts":
        data = actuals.copy()
        title = "All Contracts - Portfolio"
    else:
        cid  = contracts[contracts["contract_name"] == selected]["contract_id"].values[0]
        data = actuals[actuals["contract_id"] == cid].copy()
        title = selected

    monthly = data.groupby("month")[["budget", "actual_total", "variance"]].sum().reset_index()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Budget",  f"${monthly['budget'].sum()/1e6:.2f}M")
    c2.metric("Total Actuals", f"${monthly['actual_total'].sum()/1e6:.2f}M")
    net_var = monthly["variance"].sum()
    direction = "Favorable" if net_var >= 0 else "Unfavorable"
    c3.metric("Net Variance", f"${abs(net_var)/1e3:.0f}K {direction}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["month"], y=monthly["budget"],
        name="Budget", line=dict(color="#003865", width=2, dash="dot"), mode="lines+markers"
    ))
    fig.add_trace(go.Scatter(
        x=monthly["month"], y=monthly["actual_total"],
        name="Actuals", line=dict(color="#e85d04", width=2), mode="lines+markers"
    ))
    fig.update_layout(
        height=300, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20, b=40, l=40, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis=dict(tickprefix="$", tickformat=",.0f", gridcolor="#f1f5f9"),
        xaxis=dict(gridcolor="#f1f5f9")
    )
    st.plotly_chart(fig, use_container_width=True)

    col_pie, col_tbl = st.columns([1, 2])
    with col_pie:
        cat_totals = data[["actual_labor", "actual_odc", "actual_subcontractor"]].sum()
        fig2 = px.pie(
            names=["Direct Labor", "ODC", "Subcontractor"],
            values=cat_totals.values,
            color_discrete_sequence=["#003865", "#005a9e", "#7fb3d3"],
            hole=0.45
        )
        fig2.update_layout(height=260, margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    with col_tbl:
        disp = monthly[["month", "budget", "actual_total", "variance"]].copy()
        disp.columns = ["Month", "Budget", "Actuals", "Variance"]
        disp["Flag"] = monthly["variance"].apply(lambda v: "Favorable" if v >= 0 else "Unfavorable")
        for c in ["Budget", "Actuals", "Variance"]:
            disp[c] = disp[c].apply(lambda x: f"${x:,.0f}")
        st.dataframe(disp, use_container_width=True, hide_index=True)

    unfav = monthly[monthly["variance"] < 0]
    if len(unfav) > 0:
        worst = unfav.loc[unfav["variance"].idxmin()]
        labor_pct = data["actual_labor"].sum() / data["actual_total"].sum() * 100
        st.warning(
            f"{title} recorded {len(unfav)} unfavorable period(s). "
            f"Largest unfavorable month: {worst['month']} at ${abs(worst['variance'])/1e3:.0f}K over budget. "
            f"Direct labor represents {labor_pct:.0f}% of total spend and is the primary driver of variance. "
            f"Recommend labor utilization review by category and subcontractor invoice reconciliation."
        )
    else:
        st.success(f"{title} is tracking favorably across all periods. No corrective action required.")

# ===================================================
# MODULE 5 - FUNDING AND BURN RATE
# ===================================================
elif module == "Funding and Burn Rate":
    st.markdown("<div class='section-header'>Funding Ceiling and Burn Rate Tracker</div>", unsafe_allow_html=True)
    st.caption(
        "The government releases funding in increments. Running out of funded ceiling before the period ends "
        "means work must stop until new funding is obligated. This tracker projects when each contract "
        "approaches its ceiling. Funded ceiling values are real USASpending.gov data. "
        "Burn rate is derived from synthetic actuals."
    )

    for _, row in funding.iterrows():
        pct_used    = row["cumulative_actuals"] / row["funded_ceiling"] * 100
        months_left = row["months_until_ceiling"]
        flag        = row["ceiling_flag"]

        if flag:
            status_label = "CRITICAL"
        elif months_left < 4:
            status_label = "WATCH"
        else:
            status_label = "OK"

        with st.expander(f"{row['contract_name']} | {status_label}", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Funded Ceiling",      f"${row['funded_ceiling']/1e6:.2f}M")
            c2.metric("Costs Incurred",      f"${row['cumulative_actuals']/1e6:.2f}M")
            c3.metric("Remaining Funding",   f"${row['remaining_funding']/1e3:.0f}K")
            c4.metric("Months Until Ceiling", f"{months_left:.1f} mo.")

            gauge_color = "#dc2626" if flag else ("#d97706" if months_left < 4 else "#16a34a")
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=pct_used,
                delta={"reference": 80, "valueformat": ".1f"},
                number={"suffix": "%", "valueformat": ".1f"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": gauge_color},
                    "steps": [
                        {"range": [0,  70], "color": "#f0fdf4"},
                        {"range": [70, 85], "color": "#fef9c3"},
                        {"range": [85, 100], "color": "#fef2f2"},
                    ],
                    "threshold": {"line": {"color": "#dc2626", "width": 3}, "value": 90}
                },
                title={"text": "Funded Ceiling Utilization"}
            ))
            fig.update_layout(
                height=220, margin=dict(t=40, b=10, l=40, r=40),
                paper_bgcolor="white"
            )
            st.plotly_chart(fig, use_container_width=True)

            if flag:
                st.error(
                    f"FUNDING ALERT: Less than 2 months of funding remaining at current burn rate of "
                    f"${row['avg_monthly_burn']/1e3:.0f}K per month. "
                    f"Contracting Officer must be notified immediately to initiate a funding modification."
                )
            elif months_left < 4:
                st.warning(
                    f"Approaching ceiling within {months_left:.1f} months at current burn rate. "
                    f"Recommend initiating funding modification request within 30 days."
                )
            else:
                st.success(
                    f"Funding is sufficient for approximately {months_left:.1f} months "
                    f"at the current burn rate of ${row['avg_monthly_burn']/1e3:.0f}K per month."
                )

# ===================================================
# MODULE 6 - DATA SOURCES AND METHODOLOGY
# ===================================================
elif module == "Data Sources and Methodology":
    st.markdown("<div class='section-header'>Data Sources and Methodology</div>", unsafe_allow_html=True)

    st.markdown(
        "This project uses a hybrid data approach. Real public procurement data is used where available. "
        "Professionally modeled synthetic data is used where real data is proprietary by law."
    )

    st.markdown("#### What Is Real")
    real_data = pd.DataFrame([
        {"Data Element": "Contract award numbers",
         "Value": "75FCMC22F0046, 70T02021F7560N005, 75N97023F00001",
         "Source": "USASpending.gov"},
        {"Data Element": "Awarding agencies",
         "Value": "HHS/CMS, DHS, HHS/NIH",
         "Source": "USASpending.gov"},
        {"Data Element": "Contract ceiling values",
         "Value": "$8.07M, $1.01M, $7.34M",
         "Source": "USASpending.gov cumulative obligations"},
        {"Data Element": "NAICS codes",
         "Value": "541512, 541611, 541512",
         "Source": "USASpending.gov federal procurement records"},
        {"Data Element": "Indirect rate ranges",
         "Value": "Fringe 29-36%, Overhead 41-51%, G&A 10-15%",
         "Source": "DCAA provisional rate guidance for NAICS 541"},
        {"Data Element": "Labor bill rate benchmarks",
         "Value": "GSA Schedule SIN rates for IT and consulting",
         "Source": "GSA Multiple Award Schedule"},
    ])
    st.dataframe(real_data, use_container_width=True, hide_index=True)

    st.markdown("#### What Is Modeled (Synthetic)")
    st.info(
        "The following data elements are synthetic projections. They do not exist in any public source. "
        "In a live GovCon environment, this data lives inside Deltek Costpoint and is accessible only to "
        "authorized finance and program management personnel. Modeling this data replicates the structure "
        "of financial planning work done before and during contract execution."
    )
    synth_data = pd.DataFrame([
        {"Data Element": "Monthly cost actuals",
         "Why Synthetic": "Internal contractor records - never publicly disclosed"},
        {"Data Element": "Labor hours by category",
         "Why Synthetic": "Internal timesheet data - proprietary"},
        {"Data Element": "EAC projections",
         "Why Synthetic": "Internal monthly EAC updates - not reported to USASpending.gov"},
        {"Data Element": "Subcontractor cost breakdowns",
         "Why Synthetic": "Internal invoice data - proprietary"},
        {"Data Element": "Budget by period",
         "Why Synthetic": "Internal program baseline - proprietary"},
        {"Data Element": "Burn rate calculations",
         "Why Synthetic": "Derived from synthetic actuals"},
    ])
    st.dataframe(synth_data, use_container_width=True, hide_index=True)

    st.markdown("#### Why This Approach Is Realistic")
    st.markdown(
        "This hybrid methodology mirrors exactly what a Project Financial Analyst does in practice. "
        "The contract ceiling and agency data come from the award and are loaded into Costpoint as the project baseline. "
        "The indirect rates are set by the provisional rate agreement with DCAA and applied to all labor. "
        "The monthly actuals are what the analyst pulls from Costpoint each period and compares against the EAC. "
        "The EAC is updated monthly and defended to the program manager. "
        "The only difference between this tool and a live Costpoint environment is the source of the actuals. "
        "The structure, the math, the outputs, and the analyst commentary are identical."
    )

    st.markdown("#### Sources")
    st.markdown(
        "USASpending.gov - Official federal spending transparency database (DATA Act, P.L. 113-101). "
        "DCAA - Defense Contract Audit Agency provisional rate guidance. "
        "GSA Multiple Award Schedule - Publicly available labor category bill rates. "
        "RELI Group Inc UEI: ZZEFBLYZN5B1 | CAGE: 6VJE6."
    )
'''

app_path = r"C:\Users\balap\anaconda_projects\govcon_program_finance\app.py"
with open(app_path, "w", encoding="utf-8") as f:
    f.write(app_code)

print("✓ app.py updated successfully")
