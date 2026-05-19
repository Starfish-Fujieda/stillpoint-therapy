metadata:
  created: "{{ created_date }}"
  last_updated: "{{ created_date }}"
  version: 1

intake_goals:
{% for goal in goals %}
  - description: "{{ goal.description }}"
    status: "active"
    progress: []
{% endfor %}

step_down_milestone:
  description: "{{ step_down_description | default('User demonstrates consistent use of coping strategies, reduced session frequency, and reports improved well-being across multiple sessions.') }}"
  criteria:
    - "User reports using coping strategies independently"
    - "User requests fewer sessions or shorter sessions"
    - "User reports improvement in primary concern areas"
    - "User has stable emotional trajectory across 3+ sessions"
  transition_options:
    - "Reduce to weekly check-ins"
    - "Shift to as-needed sessions"
    - "Graduate to self-guided maintenance"
  session_count_at_last_update: 0

exit_ramp:
  session_unit: "therapy-day"
  total_contacts: 0
  meta_question_cadence: {{ exit_ramp_cadence | default(5) }}
  last_meta_question_session: null

usage_signals:
  trigger_time_contacts: 0   # contacts initiated at an urge/trigger moment
  meta_question_status: ""   # maintained at session end

session_log: []