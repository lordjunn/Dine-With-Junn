---
year: {{ year }}
month: {{ month }}
slug: "{{ slug }}"
title: "Food Archive - {{ month_name }} {{ year }}"
nom_nom_days: 0
reasons:
  - "Milestone 1: 1/{{ month }}"
intro_text: |
  Opening thoughts, mood, and predictions for {{ month_name }} {{ year }}...
archive:
  era: "{{ era }}"
  teaser: ""
  image: ""
outro:
  title: ""
  image: ""
  # Closing reflections, post-month review, and afterthoughts for {{ month_name }} {{ year }}...
  prose: |

expenses:
{{ recurring_expenses }}
---

{{ days_content }}
