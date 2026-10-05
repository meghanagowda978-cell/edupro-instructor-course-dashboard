# EduPro: Instructor Performance and Course Quality Evaluation

**Author:** Megha MP  
**Project:** Unified Mentor internship

## Live Dashboard

[Open the EduPro dashboard](https://edupro-instructor-course-dashboard-s3e2gn8ekgxljhyguugslk.streamlit.app/)

## Project Objective

Evaluate instructor ratings, course quality, teaching experience, and enrollment patterns to support evidence-based improvements on EduPro.

## Dataset

- 60 instructors
- 60 courses
- 10,000 transactions
- 887 unique instructor-course pairs

Teachers and Transactions are joined using TeacherID. Courses and Transactions are joined using CourseID.

## Tools Used

- Excel: Power Query, PivotTables, formulas, charts, and conditional formatting
- Python: pandas for data preparation and analysis
- Streamlit: interactive web dashboard
- Plotly: interactive charts
- openpyxl: Excel file reading

## Dashboard Features

- Instructor performance leaderboard
- Experience versus rating scatter plots
- Instructor rating distribution
- Course category and level heatmap
- Expertise performance comparisons
- Enrollment comparisons across instructor rating tiers
- Expertise, category, level, and rating filters
- Data validation, methodology notes, and CSV export

## Key Findings

- Average teacher rating: 3.13 out of 5
- Average course rating: 3.10 out of 5
- Experience and teacher rating correlation: 0.598
- Marketing had the highest course-category average: 3.72
- Machine Learning had the lowest course-category average: 2.66
- Advanced courses averaged 2.81
- Two instructors accounted for 60.86% of recorded enrollments
- Teacher ratings and linked course ratings showed almost no linear relationship

## KPI Definitions

- Average Teacher Rating: mean across unique instructors
- Average Course Rating: mean across unique courses
- Experience Impact Score: Pearson correlation between experience and teacher rating
- Rating Consistency Index: average population standard deviation of instructors' linked course ratings; a portfolio consistency proxy
- Enrollment Influence Ratio: average transactions per High-tier instructor divided by average transactions per instructor in the current selection

High-tier instructors have ratings of 4 or above. Dashboard calculations use the current filter selection.

## Recommendations

Review lower-rated courses, collect instructor-specific feedback and review counts, provide training based on confirmed needs, and investigate enrollment concentration.

## Limitations

Transactions are an enrollment proxy and do not establish attendance or completion. Course ratings are shared across multiple instructors, so they cannot isolate individual teaching effectiveness. Correlations describe associations and do not establish causation.

## Reports

- [Research Paper](EduPro_Research_Paper.pdf)
- [Executive Summary](EduPro_Executive_Summary.pdf)

## Run Locally

Keep app.py, edupro.xlsx, and requirements.txt in the same folder.

Install the required packages:

```bash
python -m pip install -r requirements.txt
```

Start the dashboard:

```bash
python -m streamlit run app.py
```

The application reads the Teachers, Courses, and Transactions sheets from edupro.xlsx.
