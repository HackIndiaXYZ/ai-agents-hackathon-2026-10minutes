"""
features/ — User-facing financial-inclusion features.

Each module turns the user's profile + knowledge graph + live data into a
concrete, actionable output:

  schemes.py    → Scheme Eligibility Engine
  documents.py  → Document Checklist Generator
  complaints.py → Guided Complaint Filing
  literacy.py   → Literacy Progress Dashboard
  news_feed.py  → Fraud Alert Feed (live Google News RSS)

Real data only. Government / scheme / complaint info comes from Gemini grounded
on live Google Search (gemini_grounded.py); fraud alerts come from live news RSS.
Nothing in this package hardcodes scheme lists, document lists, or news.
"""
