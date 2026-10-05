"""EduPro dashboard — filters, unique records, and descriptive comparisons."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="EduPro | Teaching Quality", page_icon="🎓", layout="wide")
st.title("EduPro · Instructor & Course Quality")
st.caption("Explore teaching ratings, course quality and enrollment patterns.")


# Cache avoids reading the same workbook every time a filter changes.
@st.cache_data
def load_data(path, modified_time):
    sheets = pd.read_excel(path, sheet_name=["Teachers", "Courses", "Transactions"])
    return sheets["Teachers"], sheets["Courses"], sheets["Transactions"]


def display_number(value, places=2):
    """Use consistent decimal rounding; missing statistics display as N/A."""
    if pd.isna(value):
        return "N/A"
    rounded = Decimal(str(round(float(value), 12))).quantize(Decimal("1").scaleb(-places), rounding=ROUND_HALF_UP)
    return f"{rounded:.{places}f}"


def correlation(frame, first, second):
    valid = frame[[first, second]].dropna()
    if len(valid) < 2 or valid[first].nunique() < 2 or valid[second].nunique() < 2:
        return float("nan")
    return valid[first].corr(valid[second])


# Resolve the workbook relative to this Python file, wherever it is launched.
workbook = Path(__file__).resolve().parent / "edupro.xlsx"
if not workbook.exists():
    st.error("Put edupro.xlsx in the same folder as app.py, then rerun the app.")
    st.stop()
try:
    teachers, courses, transactions = load_data(str(workbook), workbook.stat().st_mtime)
    required = {
        "Teachers": (teachers, ["TeacherID", "TeacherName", "Expertise", "YearsOfExperience", "TeacherRating"]),
        "Courses": (courses, ["CourseID", "CourseName", "CourseCategory", "CourseLevel", "CourseRating"]),
        "Transactions": (transactions, ["TransactionID", "TeacherID", "CourseID"]),
    }
    for name, (frame, columns) in required.items():
        missing = set(columns) - set(frame.columns)
        if missing:
            raise ValueError(f"{name}: missing columns {', '.join(sorted(missing))}")
        if frame[columns].isna().any().any():
            raise ValueError(f"{name}: required fields contain blank values.")
    for frame, identifier in [(teachers, "TeacherID"), (courses, "CourseID"), (transactions, "TransactionID")]:
        if frame[identifier].duplicated().any():
            raise ValueError(f"Duplicate {identifier} values need review.")
    for frame, column in [(teachers, "TeacherRating"), (teachers, "YearsOfExperience"), (courses, "CourseRating")]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if not frame[column].ge(0).all():
            raise ValueError(f"{column} must contain non-negative numbers.")
    if not teachers["TeacherRating"].between(0, 5).all() or not courses["CourseRating"].between(0, 5).all():
        raise ValueError("Ratings must be between 0 and 5.")
    if not transactions["TeacherID"].isin(teachers["TeacherID"]).all():
        raise ValueError("Some transactions reference an unknown TeacherID.")
    if not transactions["CourseID"].isin(courses["CourseID"]).all():
        raise ValueError("Some transactions reference an unknown CourseID.")
    analysis = transactions.merge(teachers, on="TeacherID", how="left", validate="many_to_one")
    analysis = analysis.merge(courses, on="CourseID", how="left", validate="many_to_one")
except (ValueError, KeyError, ImportError, OSError) as error:
    st.error(f"Please check the workbook: {error}")
    st.stop()

# Create each control once, before calculations that depend on it.
st.sidebar.header("Filter the dashboard")
expertise_options = sorted(teachers["Expertise"].unique())
category_options = sorted(courses["CourseCategory"].unique())
level_options = sorted(courses["CourseLevel"].unique())
selected_expertise = st.sidebar.multiselect("Instructor Expertise", expertise_options, default=expertise_options, key="expertise")
selected_categories = st.sidebar.multiselect("Course Category", category_options, default=category_options, key="category")
selected_levels = st.sidebar.multiselect("Course Level", level_options, default=level_options, key="level")
rating_range = st.sidebar.slider("Teacher Rating Range", 0.0, 5.0, (0.0, 5.0), 0.1, key="teacher_rating")
course_rating_range = st.sidebar.slider("Course Rating Range", 0.0, 5.0, (0.0, 5.0), 0.1, key="course_rating")
st.sidebar.caption("All views use these filters. Clearing a selection gives no matches.")

# Filter transactions first, then recover unique teachers, courses and pairs.
# This avoids counting a popular instructor's rating thousands of times.
filtered_analysis = analysis[
    analysis["Expertise"].isin(selected_expertise)
    & analysis["CourseCategory"].isin(selected_categories)
    & analysis["CourseLevel"].isin(selected_levels)
    & analysis["TeacherRating"].between(*rating_range)
    & analysis["CourseRating"].between(*course_rating_range)
].copy()
if filtered_analysis.empty:
    st.info("No matching records. Select an expertise, category and level, or widen the rating ranges.")
    st.stop()
filtered_teachers = teachers[teachers["TeacherID"].isin(filtered_analysis["TeacherID"])].copy()
filtered_courses = courses[courses["CourseID"].isin(filtered_analysis["CourseID"])].copy()
pairs = filtered_analysis.drop_duplicates(["TeacherID", "CourseID"])

st.caption(f"Current selection: {len(filtered_teachers):,} instructors · {len(filtered_courses):,} courses · "
           f"{len(filtered_analysis):,} transactions · {len(pairs):,} instructor–course pairs")
st.caption("Only instructors and courses linked by matching transactions are included. Transactions are an enrollment proxy.")

average_teacher_rating = filtered_teachers["TeacherRating"].mean()
average_course_rating = filtered_courses["CourseRating"].mean()
experience_impact = correlation(filtered_teachers, "YearsOfExperience", "TeacherRating")
portfolio = pairs.groupby("TeacherID").agg(CourseCount=("CourseID", "size"), AverageCourseRating=("CourseRating", "mean"))
portfolio["RatingSpread"] = pairs.groupby("TeacherID")["CourseRating"].std(ddof=0)
# A single course cannot establish consistency across courses.
portfolio.loc[portfolio["CourseCount"] < 2, "RatingSpread"] = float("nan")
consistency_index = portfolio["RatingSpread"].mean()
high_rated_teachers = filtered_teachers[filtered_teachers["TeacherRating"] >= 4]
high_rated_transactions = filtered_analysis[filtered_analysis["TeacherRating"] >= 4]
selection_average = len(filtered_analysis) / len(filtered_teachers)
enrollment_ratio = (len(high_rated_transactions) / len(high_rated_teachers) / selection_average
                    if len(high_rated_teachers) else float("nan"))

metrics = st.columns(5)
metrics[0].metric("Average Teacher Rating", display_number(average_teacher_rating))
metrics[1].metric("Average Course Rating", display_number(average_course_rating))
metrics[2].metric("Experience Impact Score", display_number(experience_impact, 3))
metrics[3].metric("Rating Consistency Index", display_number(consistency_index))
metrics[4].metric("Enrollment Influence Ratio", display_number(enrollment_ratio))

instructor_tab, course_tab, enrollment_tab, notes_tab = st.tabs(["Instructors", "Course quality", "Enrollments", "Methods & data checks"])
labels = {"TeacherRating": "Teacher rating", "YearsOfExperience": "Experience (years)", "CourseRating": "Course rating"}
with instructor_tab:
    st.subheader("Instructor Performance Leaderboard")
    enrollment_counts = filtered_analysis.groupby("TeacherID").size().rename("Enrollments")
    leaderboard = filtered_teachers.merge(enrollment_counts, on="TeacherID", how="left").merge(portfolio, on="TeacherID", how="left")
    leaderboard = leaderboard.sort_values(["TeacherRating", "TeacherName"], ascending=[False, True])
    st.dataframe(leaderboard[["TeacherID", "TeacherName", "Expertise", "YearsOfExperience", "TeacherRating", "Enrollments", "CourseCount", "AverageCourseRating", "RatingSpread"]].round(2), hide_index=True)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(px.scatter(filtered_teachers, x="YearsOfExperience", y="TeacherRating", hover_name="TeacherName", color="Expertise", range_y=[0, 5], labels=labels, title="Experience vs Teacher Rating"), use_container_width=True)
    with right:
        st.plotly_chart(px.histogram(filtered_teachers, x="TeacherRating", nbins=10, range_x=[0, 5], labels=labels, title="Distribution of Instructor Ratings"), use_container_width=True)
    expertise_ratings = filtered_teachers.groupby("Expertise", as_index=False).agg(TeacherRating=("TeacherRating", "mean"), Instructors=("TeacherID", "size"))
    expertise_ratings = expertise_ratings.sort_values("TeacherRating")
    st.plotly_chart(px.bar(expertise_ratings, x="TeacherRating", y="Expertise", orientation="h", text_auto=".2f", hover_data=["Instructors"], range_x=[0, 5], labels=labels, title="Average Teacher Rating by Expertise"), use_container_width=True)

with course_tab:
    quality_table = filtered_courses.pivot_table(index="CourseCategory", columns="CourseLevel", values="CourseRating", aggfunc="mean")
    level_order = [level for level in ["Beginner", "Intermediate", "Advanced"] if level in quality_table.columns]
    level_order += [level for level in quality_table.columns if level not in level_order]
    quality_table = quality_table.reindex(columns=level_order)
    st.plotly_chart(px.imshow(quality_table, text_auto=".2f", color_continuous_scale="RdYlGn", zmin=0, zmax=5, aspect="auto", title="Course Quality by Category and Level", labels={"color": "Average rating"}), use_container_width=True)
    st.caption("Each course is counted once. Blank cells mean no matching courses; a high average from one course does not establish consistency.")
    with st.expander("Number of courses behind each heatmap cell"):
        counts = filtered_courses.pivot_table(index="CourseCategory", columns="CourseLevel", values="CourseID", aggfunc="count", fill_value=0)
        st.dataframe(counts.reindex(index=quality_table.index, columns=level_order))
    expertise_quality = pairs.groupby("Expertise", as_index=False).agg(CourseRating=("CourseRating", "mean"), Pairs=("CourseID", "size"), Courses=("CourseID", "nunique"), Instructors=("TeacherID", "nunique"))
    st.plotly_chart(px.bar(expertise_quality.sort_values("CourseRating"), x="CourseRating", y="Expertise", orientation="h", text_auto=".2f", range_x=[0, 5], hover_data=["Pairs", "Courses", "Instructors"], labels=labels, title="Linked Course Ratings by Instructor Expertise"), use_container_width=True)
    st.caption("Each unique instructor–course pair has equal weight here. A shared course can appear for several instructors.")
    a, b = st.columns(2)
    a.metric("Teacher vs course rating (pair correlation)", display_number(correlation(pairs, "TeacherRating", "CourseRating"), 3))
    b.metric("Experience vs course rating (pair correlation)", display_number(correlation(pairs, "YearsOfExperience", "CourseRating"), 3))
    st.dataframe(filtered_courses[["CourseID", "CourseName", "CourseCategory", "CourseLevel", "CourseRating"]], hide_index=True)

with enrollment_tab:
    def rating_tier(rating):
        if rating >= 4:
            return "High (4–5)"
        if rating >= 3:
            return "Mid (3–<4)"
        return "Low (<3)"
    tier_teachers = filtered_teachers.copy()
    tier_teachers["Tier"] = tier_teachers["TeacherRating"].map(rating_tier)
    tier_teachers = tier_teachers.merge(enrollment_counts, on="TeacherID", how="left")
    tiers = tier_teachers.groupby("Tier", as_index=False).agg(Instructors=("TeacherID", "size"), Enrollments=("Enrollments", "sum"))
    tiers["EnrollmentsPerInstructor"] = tiers["Enrollments"] / tiers["Instructors"]
    pair_tiers = pairs.assign(Tier=pairs["TeacherRating"].map(rating_tier))
    tiers = tiers.merge(pair_tiers.groupby("Tier", as_index=False).agg(AverageCourseRating=("CourseRating", "mean"), Pairs=("CourseID", "size")), on="Tier")
    st.dataframe(tiers.round(2), hide_index=True)
    st.plotly_chart(px.bar(tiers, x="Tier", y="EnrollmentsPerInstructor", text_auto=".2f", title="Enrollments per Instructor by Rating Tier", labels={"EnrollmentsPerInstructor": "Transactions per instructor"}), use_container_width=True)
    top = leaderboard.nlargest(10, "Enrollments").sort_values("Enrollments")
    st.plotly_chart(px.bar(top, x="Enrollments", y="TeacherName", orientation="h", text_auto=True, title="Top Instructors by Enrollment Volume", labels={"TeacherName": "Instructor", "Enrollments": "Transactions"}), use_container_width=True)
    top_two_share = leaderboard.nlargest(2, "Enrollments")["Enrollments"].sum() / len(filtered_analysis) * 100
    st.write(f"Top two instructors account for {top_two_share:.2f}% of transactions in this selection.")
    st.caption("Enrollment differences are associations. Pricing, promotion and availability may also affect demand.")

with notes_tab:
    st.markdown("""
**How filters work:** Expertise and teacher ratings select instructors; category, level and course ratings select courses. Matching transactions connect them. All dashboard results use that selection.

**Rating averages:** Each matching instructor or course is counted once, regardless of transaction volume.

**Experience Impact Score:** Pearson correlation between experience and teacher rating, using one row per instructor. Correlation is association, not proof of an experience effect. N/A means insufficient data or no variation.

**Rating Consistency Index (proxy):** Mean population standard deviation of linked course ratings across instructors with at least two matching courses. Lower values mean less spread, not necessarily higher quality. It is a project-defined portfolio measure, not a validated reliability score.

**Enrollment Influence Ratio:** Transactions per high-rated instructor (rating ≥ 4), divided by transactions per instructor across the current selection. With all filters open, the denominator is the platform average. N/A means no matching high-rated instructor. This measures association, not instructor-caused demand.

**Data limitations:** Course ratings are shared across instructors assigned to the same course. Pair correlations are descriptive because pairs reuse teachers and courses. Review counts, individual learner feedback and completion outcomes are unavailable. Transactions are treated as enrollment records, including any zero-amount records; they do not establish course completion or unique learners.
""")
    all_pairs = analysis.drop_duplicates(["TeacherID", "CourseID"])
    checks = pd.DataFrame({"Check": ["Teachers", "Courses", "Original transactions", "Joined transaction rows", "Unique instructor–course pairs", "Unmatched IDs"], "Result": [len(teachers), len(courses), len(transactions), len(analysis), len(all_pairs), 0]})
    st.dataframe(checks, hide_index=True)
    st.download_button("Download selected instructor summary", leaderboard.to_csv(index=False).encode("utf-8"), "edupro_instructors.csv", "text/csv")
