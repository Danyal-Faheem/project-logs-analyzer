import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re

st.set_page_config(page_title="Logs Analyzer", layout="wide")
st.title("🧠 Project Logs Analyzer")

# File uploader
uploaded_files = st.file_uploader("Upload one or more CSV log files", type="csv", accept_multiple_files=True)

if uploaded_files:
    try:
        # Load and combine all files
        df_list = [pd.read_csv(file) for file in uploaded_files]
        df = pd.concat(df_list, ignore_index=True)

        # Clean columns
        df.columns = df.columns.str.strip()

        required_columns = ['Date', 'Hours', 'Description', 'SubTeam']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            st.error(f"❌ Missing required columns: {', '.join(missing)}")
            st.stop()

        # Convert and clean data
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Hours'] = pd.to_numeric(df['Hours'], errors='coerce')
        df.dropna(subset=['Date', 'Hours'], inplace=True)
        df['DayOfWeek'] = df['Date'].dt.day_name()

        # Extract Tasks
        def extract_tasks(desc):
            if isinstance(desc, str):
                return re.findall(r'\[(.*?)\]', desc)
            return []

        df['Tasks'] = df['Description'].apply(extract_tasks)
        df_exploded = df.explode('Tasks')
        df_exploded = df_exploded[df_exploded['Tasks'].notna() & (df_exploded['Tasks'] != '')]

        st.header("📊 Visualizations")

        # === Chart 1: Avg Hours per Weekday ===
        st.subheader("⏱ Average Daily Hours by Weekday")

        daily_totals = df.groupby(['Date', 'DayOfWeek'])['Hours'].sum().reset_index()
        weekday_avg = daily_totals.groupby('DayOfWeek')['Hours'].mean()

        ordered_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_avg = weekday_avg.loc[weekday_avg.index.intersection(ordered_days)]
        weekday_avg = weekday_avg.reindex([d for d in ordered_days if d in weekday_avg.index])

        if weekday_avg.empty:
            st.info("ℹ️ Not enough data to display average daily hours.")
        else:
            fig1, ax1 = plt.subplots()
            weekday_avg.plot(kind='bar', color='mediumseagreen', edgecolor='black', ax=ax1)
            ax1.set_title("Average Daily Hours by Weekday")
            ax1.set_xlabel("Day")
            ax1.set_ylabel("Average Hours")
            ax1.tick_params(axis='x', rotation=45)
            st.pyplot(fig1)

        # === Chart 2: Task Type Percentages ===
        st.subheader("🧩 Percentage of Time Spent on Each Task")

        task_summary = df_exploded.groupby('Tasks')['Hours'].sum()
        task_summary = task_summary[task_summary.index.notna() & (task_summary.index != '')]

        if task_summary.empty:
            st.info("ℹ️ Not enough task data to display pie chart.")
        else:
            fig2, ax2 = plt.subplots(figsize=(6, 6))
            ax2.pie(task_summary, labels=task_summary.index, autopct='%1.1f%%', startangle=140)
            ax2.set_title("Time Spent by Task Type")
            ax2.axis('equal')
            st.pyplot(fig2)

        # === Chart 3: Task % by Weekday ===
        st.subheader("📅 Task Breakdown by Day (%)")

        grouped_day_task = df_exploded.groupby(['DayOfWeek', 'Tasks'])['Hours'].sum().reset_index()
        pivot_day_task = grouped_day_task.pivot(index='DayOfWeek', columns='Tasks', values='Hours').fillna(0)
        pivot_day_task = pivot_day_task.reindex([d for d in ordered_days if d in pivot_day_task.index])
        pivot_day_task_percent = pivot_day_task.div(pivot_day_task.sum(axis=1), axis=0) * 100

        if pivot_day_task_percent.empty:
            st.info("ℹ️ Not enough task data to break down by weekday.")
        else:
            fig3, ax3 = plt.subplots(figsize=(12, 6))
            pivot_day_task_percent.plot(kind='bar', stacked=True, colormap='tab20', ax=ax3)
            ax3.set_ylabel("Percentage")
            ax3.set_title("Task Breakdown by Weekday (%)")
            ax3.legend(title='Task Type', bbox_to_anchor=(1.05, 1), loc='upper left')
            ax3.tick_params(axis='x', rotation=45)
            st.pyplot(fig3)

        # === Chart 4: SubTeam % per Day ===
        st.subheader("📂 Percentage of Time Spent Each Day on Each SubTeam")

        if 'SubTeam' not in df.columns:
            st.warning("⚠️ 'SubTeam' column missing, skipping subteam breakdown.")
        else:
            subteam_by_day = df.groupby(['DayOfWeek', 'SubTeam'])['Hours'].sum().reset_index()
            pivot_subteam = subteam_by_day.pivot(index='DayOfWeek', columns='SubTeam', values='Hours').fillna(0)
            pivot_subteam = pivot_subteam.reindex([d for d in ordered_days if d in pivot_subteam.index])
            pivot_subteam_percent = pivot_subteam.div(pivot_subteam.sum(axis=1), axis=0) * 100

            if pivot_subteam_percent.empty:
                st.info("ℹ️ Not enough SubTeam data to display stacked chart.")
            else:
                fig4, ax4 = plt.subplots(figsize=(12, 6))
                pivot_subteam_percent.plot(kind='bar', stacked=True, colormap='Set3', ax=ax4)
                ax4.set_ylabel("Percentage")
                ax4.set_title("Time Spent on SubTeams by Day (%)")
                ax4.legend(title='SubTeam', bbox_to_anchor=(1.05, 1), loc='upper left')
                ax4.tick_params(axis='x', rotation=45)
                st.pyplot(fig4)

        # === Chart 5: Pie per SubTeam ===
        st.subheader("🎯 Task Breakdown per SubTeam")

        grouped_subteam_task = df_exploded.groupby(['SubTeam', 'Tasks'])['Hours'].sum().reset_index()

        if grouped_subteam_task.empty:
            st.info("ℹ️ Not enough SubTeam + Task data to render pie charts.")
        else:
            subteams = grouped_subteam_task['SubTeam'].unique()
            num_subteams = len(subteams)
            cols = st.columns(min(num_subteams, 3))  # Up to 3 per row

            for idx, subteam in enumerate(subteams):
                subset = grouped_subteam_task[grouped_subteam_task['SubTeam'] == subteam].set_index('Tasks')['Hours']
                if subset.sum() == 0:
                    continue
                with cols[idx % len(cols)]:
                    fig, ax = plt.subplots(figsize=(4, 4))
                    ax.pie(subset, labels=subset.index, autopct='%1.1f%%', startangle=140)
                    ax.set_title(f"{subteam}")
                    ax.axis('equal')
                    st.pyplot(fig)

    except Exception as e:
        st.error(f"🚨 An error occurred while processing the files: {str(e)}")
