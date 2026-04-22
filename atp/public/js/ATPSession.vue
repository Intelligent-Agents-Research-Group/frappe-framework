<template>
  <div class="atp-session">

    <!-- ── Scenario Selector ─────────────────────────────────────────────── -->
    <div v-if="view === 'select'" class="atp-session__select">
      <div class="atp-session__select-card">
        <h1 class="atp-session__title">Training Session</h1>
        <p class="atp-session__subtitle">Choose a scenario to begin</p>

        <div v-if="loadingScenarios" class="atp-session__loading">Loading scenarios…</div>

        <div v-else class="atp-session__scenarios">
          <div
            v-for="s in scenarios"
            :key="s.name"
            class="atp-session__scenario-card"
            :class="{ selected: selectedScenario === s.name }"
            @click="selectedScenario = s.name"
          >
            <div class="atp-session__scenario-title">{{ s.title }}</div>
            <div class="atp-session__scenario-desc">{{ s.description }}</div>
            <div class="atp-session__scenario-meta">
              <span class="badge">{{ s.modality }}</span>
              <span v-if="s.requires_pair" class="badge badge--pair">Pair</span>
            </div>
          </div>
        </div>

        <div v-if="selectError" class="atp-session__error">{{ selectError }}</div>

        <button
          class="atp-session__btn atp-session__btn--primary"
          :disabled="!selectedScenario || startingSession"
          @click="startSession"
        >
          {{ startingSession ? 'Starting…' : 'Start Session' }}
        </button>
      </div>
    </div>

    <!-- ── Active Session ────────────────────────────────────────────────── -->
    <div v-else-if="view === 'session'" class="atp-session__active">

      <!-- Header -->
      <div class="atp-session__header">
        <div class="atp-session__scenario-name">{{ scenarioTitle }}</div>
        <div class="atp-session__meta">
          <span class="atp-session__turn-count">Turn {{ turnCount }}</span>
          <div class="atp-session__competency-bar">
            <div
              v-for="comp in topCompetencies"
              :key="comp.id"
              class="atp-session__comp-chip"
              :title="comp.label"
            >
              <span class="atp-session__comp-label">{{ comp.label }}</span>
              <div class="atp-session__comp-fill" :style="{ width: (comp.estimate * 100) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Affective state -->
      <div class="atp-session__affective" v-if="affectiveState">
        <span class="affective-chip" :class="engagementClass">
          Engagement {{ pct(affectiveState.engagement) }}
        </span>
        <span class="affective-chip" :class="frustrationClass">
          Frustration {{ pct(affectiveState.frustration) }}
        </span>
        <span class="affective-chip">
          Confidence {{ pct(affectiveState.confidence) }}
        </span>
      </div>

      <!-- Conversation -->
      <div class="atp-session__conversation" ref="convEl">
        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="atp-session__msg"
          :class="'atp-session__msg--' + msg.role"
        >
          <div class="atp-session__msg-bubble">
            <div v-if="msg.role === 'agent'" class="atp-session__msg-speaker">
              {{ msg.speaker || 'Agent' }}
              <span v-if="msg.expression" class="atp-session__nonverbal">[{{ msg.expression }}]</span>
            </div>
            <div class="atp-session__msg-text">{{ msg.text }}</div>
            <div v-if="msg.competencyUpdates?.length" class="atp-session__comp-updates">
              <span
                v-for="u in msg.competencyUpdates"
                :key="u.competency_node_id"
                class="atp-session__comp-spark"
                :class="u.new_estimate > u.previous_estimate ? 'spark--up' : 'spark--down'"
              >
                {{ u.competency_label }} {{ u.new_estimate > u.previous_estimate ? '↑' : '↓' }}
              </span>
            </div>
            <div v-if="msg.intervention" class="atp-session__intervention">
              💡 {{ msg.intervention.content }}
            </div>
          </div>
        </div>
        <div v-if="agentTyping" class="atp-session__msg atp-session__msg--agent">
          <div class="atp-session__msg-bubble atp-session__typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <!-- Situation text (current step) -->
      <div v-if="currentSituationText" class="atp-session__situation">
        {{ currentSituationText }}
      </div>

      <!-- Input area -->
      <div class="atp-session__input-area" v-if="sessionStatus === 'in_progress'">
        <textarea
          v-model="userInput"
          class="atp-session__textarea"
          placeholder="Type your response…"
          :disabled="sending"
          rows="3"
          @keydown.ctrl.enter="sendTurn"
          @keydown.meta.enter="sendTurn"
        ></textarea>
        <div class="atp-session__input-actions">
          <span class="atp-session__hint">Ctrl+Enter to send</span>
          <button
            class="atp-session__btn atp-session__btn--primary"
            :disabled="!userInput.trim() || sending"
            @click="sendTurn"
          >
            {{ sending ? 'Sending…' : 'Send' }}
          </button>
        </div>
        <div v-if="turnError" class="atp-session__error">{{ turnError }}</div>
      </div>

      <!-- Debrief ready -->
      <div v-if="sessionStatus === 'debrief_ready'" class="atp-session__debrief-prompt">
        <button class="atp-session__btn atp-session__btn--primary" @click="endSession">
          See Debrief
        </button>
      </div>
    </div>

    <!-- ── Debrief ────────────────────────────────────────────────────────── -->
    <div v-else-if="view === 'debrief'" class="atp-session__debrief">
      <h2 class="atp-session__debrief-title">Session Debrief</h2>

      <div v-if="debrief" class="atp-session__debrief-content">
        <p class="atp-session__debrief-summary">{{ debrief.summary_text }}</p>

        <div v-if="debrief.competency_highlights?.length" class="atp-session__debrief-section">
          <h3>Competencies</h3>
          <div
            v-for="h in debrief.competency_highlights"
            :key="h.competency_label"
            class="atp-session__debrief-comp"
            :class="'perf--' + h.performance"
          >
            <span class="atp-session__debrief-comp-label">{{ h.competency_label }}</span>
            <span class="atp-session__debrief-comp-perf">{{ h.performance }}</span>
            <p class="atp-session__debrief-comp-note">{{ h.note }}</p>
          </div>
        </div>

        <div v-if="debrief.recommended_focus?.length" class="atp-session__debrief-section">
          <h3>Focus next</h3>
          <ul>
            <li v-for="f in debrief.recommended_focus" :key="f">{{ f }}</li>
          </ul>
        </div>
      </div>

      <div v-else class="atp-session__loading">Loading debrief…</div>

      <button class="atp-session__btn atp-session__btn--secondary" @click="reset">
        Start New Session
      </button>
    </div>

  </div>
</template>

<script>
import { createApp, ref, computed, nextTick, onMounted } from "vue";

const ENGINE_BASE = "http://localhost:8010";

export default {
  name: "ATPSession",
  props: {
    enrollmentName: { type: String, default: null },
    scenarioId: { type: String, default: null },
  },
  setup(props) {
    const view = ref("select");
    const scenarios = ref([]);
    const loadingScenarios = ref(true);
    const selectedScenario = ref(null);
    const selectError = ref(null);
    const startingSession = ref(false);

    const sessionId = ref(null);
    const learnerId = ref(null);
    const scenarioTitle = ref("");
    const messages = ref([]);
    const userInput = ref("");
    const sending = ref(false);
    const agentTyping = ref(false);
    const turnCount = ref(0);
    const sessionStatus = ref("in_progress");
    const turnError = ref(null);
    const currentSituationText = ref("");

    const competencyEstimates = ref({});
    const competencyLabels = ref({});
    const affectiveState = ref(null);
    const debrief = ref(null);

    const convEl = ref(null);

    // ── Computed ────────────────────────────────────────────────────────────

    const topCompetencies = computed(() => {
      return Object.entries(competencyEstimates.value)
        .slice(0, 4)
        .map(([id, estimate]) => ({
          id,
          label: competencyLabels.value[id] || id,
          estimate,
        }));
    });

    const engagementClass = computed(() => {
      const e = affectiveState.value?.engagement || 0;
      return e > 0.6 ? "chip--good" : e > 0.3 ? "chip--mid" : "chip--low";
    });

    const frustrationClass = computed(() => {
      const f = affectiveState.value?.frustration || 0;
      return f > 0.7 ? "chip--bad" : f > 0.4 ? "chip--mid" : "chip--good";
    });

    // ── Methods ──────────────────────────────────────────────────────────────

    function pct(v) {
      return Math.round((v || 0) * 100) + "%";
    }

    async function frappeCall(method, args = {}) {
      const resp = await fetch(`/api/method/${method}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": frappe.csrf_token },
        body: JSON.stringify(args),
      });
      const data = await resp.json();
      if (data.exc) throw new Error(data.exc);
      return data.message;
    }

    async function enginePost(path, body) {
      const resp = await fetch(`${ENGINE_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err?.error?.message || `Engine error ${resp.status}`);
      }
      return resp.json();
    }

    async function loadScenarios() {
      loadingScenarios.value = true;
      try {
        scenarios.value = await frappeCall("atp.atp.api_v2.get_scenario_list");
      } catch (e) {
        selectError.value = "Failed to load scenarios: " + e.message;
      } finally {
        loadingScenarios.value = false;
      }
    }

    async function startSession() {
      startingSession.value = true;
      selectError.value = null;
      try {
        const result = await frappeCall("atp.atp.api_v2.create_and_submit_session", {
          scenario_id: selectedScenario.value,
        });
        sessionId.value = result.session_id;
        learnerId.value = result.learner_id;

        const scenario = scenarios.value.find((s) => s.name === selectedScenario.value);
        scenarioTitle.value = scenario?.title || selectedScenario.value;

        await connectToEngine(result.session_id, result.learner_id);
      } catch (e) {
        selectError.value = "Failed to start session: " + e.message;
      } finally {
        startingSession.value = false;
      }
    }

    async function connectToEngine(sessId, lrnId) {
      try {
        const resp = await fetch(`${ENGINE_BASE}/learner/state/${sessId}`);
        if (resp.ok) {
          const state = await resp.json();
          applyLearnerState(state);
        }
      } catch (_) {
        // Engine may not have state yet — that's OK
      }

      view.value = "session";

      messages.value.push({
        role: "system",
        text: "Session started. The scenario is loading…",
      });

      await scrollToBottom();
    }

    function applyLearnerState(state) {
      if (state.competency_estimates) {
        competencyEstimates.value = state.competency_estimates;
      }
      if (state.affective_state) {
        affectiveState.value = state.affective_state;
      }
    }

    async function sendTurn() {
      const input = userInput.value.trim();
      if (!input || sending.value) return;

      sending.value = true;
      turnError.value = null;
      userInput.value = "";

      messages.value.push({ role: "learner", text: input });
      await scrollToBottom();
      agentTyping.value = true;
      turnCount.value++;

      const turnId = `turn_${Date.now()}`;

      try {
        const resp = await enginePost("/session/turn", {
          session_id: sessionId.value,
          learner_id: learnerId.value,
          turn_id: turnId,
          turn_type: "conversational",
          learner_input: input,
          input_modality: "text",
          timestamp: new Date().toISOString(),
        });

        agentTyping.value = false;

        // Update competency estimates
        if (resp.competency_updates) {
          for (const u of resp.competency_updates) {
            competencyEstimates.value[u.competency_node_id] = u.new_estimate;
            competencyLabels.value[u.competency_node_id] = u.competency_label;
          }
        }

        // Render each agent's response
        for (const ar of resp.agent_responses || []) {
          messages.value.push({
            role: "agent",
            speaker: ar.character_id,
            text: ar.spoken_text,
            expression: ar.nonverbal_cues?.expression,
            competencyUpdates: resp.competency_updates || [],
            intervention: resp.intervention || null,
          });
        }

        // Update session state
        if (resp.next_step?.situation_text) {
          currentSituationText.value = resp.next_step.situation_text;
        }
        sessionStatus.value = resp.session_status || "in_progress";

        // Update affective state from the engine's learner state
        if (resp.session_status !== "debrief_ready") {
          try {
            const state = await fetch(`${ENGINE_BASE}/learner/state/${sessionId.value}`).then((r) => r.json());
            applyLearnerState(state);
          } catch (_) {}
        }

        await scrollToBottom();
      } catch (e) {
        agentTyping.value = false;
        turnError.value = "Error: " + e.message;
      } finally {
        sending.value = false;
      }
    }

    async function endSession() {
      try {
        const resp = await enginePost("/session/end", {
          session_id: sessionId.value,
          learner_id: learnerId.value,
          end_reason: "completed",
          learner_initiated: true,
        });
        debrief.value = resp.debrief || null;
        // Mark the v1 enrollment complete when launched from course flow
        if (props.enrollmentName) {
          try {
            await frappeCall("atp.atp.api.complete_course", { enrollment_name: props.enrollmentName });
          } catch (_) {}
        }
        view.value = "debrief";
      } catch (e) {
        turnError.value = "Failed to end session: " + e.message;
      }
    }

    function reset() {
      // When launched from course flow, go back to dashboard rather than showing the standalone selector
      if (props.enrollmentName) {
        frappe.set_route("student_dashboard");
        return;
      }
      view.value = "select";
      sessionId.value = null;
      learnerId.value = null;
      messages.value = [];
      turnCount.value = 0;
      sessionStatus.value = "in_progress";
      competencyEstimates.value = {};
      affectiveState.value = null;
      debrief.value = null;
      currentSituationText.value = "";
      selectedScenario.value = null;
    }

    async function scrollToBottom() {
      await nextTick();
      if (convEl.value) {
        convEl.value.scrollTop = convEl.value.scrollHeight;
      }
    }

    // ── Lifecycle ────────────────────────────────────────────────────────────

    onMounted(async () => {
      // Launched from course flow with a pre-selected scenario
      if (props.scenarioId) {
        selectedScenario.value = props.scenarioId;
        // Load scenario title for display
        try {
          const list = await frappeCall("atp.atp.api_v2.get_scenario_list");
          const match = (list || []).find((s) => s.name === props.scenarioId);
          if (match) scenarioTitle.value = match.title;
          else scenarioTitle.value = props.scenarioId;
        } catch { scenarioTitle.value = props.scenarioId; }
        await startSession();
        return;
      }
      // Standalone mode: show selector
      await loadScenarios();
    });

    return {
      view, scenarios, loadingScenarios, selectedScenario, selectError,
      startingSession, startSession,
      sessionId, learnerId, scenarioTitle, messages, userInput, sending,
      agentTyping, turnCount, sessionStatus, turnError, currentSituationText,
      competencyEstimates, topCompetencies, affectiveState, engagementClass,
      frustrationClass, debrief, convEl,
      pct, sendTurn, endSession, reset,
      enrollmentName: props.enrollmentName,
    };
  },
};
</script>

<style scoped>
.atp-session {
  --atp-bg: #f9fafb;
  --atp-surface: #ffffff;
  --atp-border: #e5e7eb;
  --atp-text: #111827;
  --atp-muted: #6b7280;
  --atp-accent: #3b82f6;
  --atp-agent-bg: #eff6ff;
  --atp-learner-bg: #f3f4f6;
  --atp-good: #16a34a;
  --atp-mid: #d97706;
  --atp-bad: #dc2626;

  min-height: 100vh;
  background: var(--atp-bg);
  color: var(--atp-text);
  font-family: 'Inter', system-ui, sans-serif;
  display: flex;
  flex-direction: column;
}

/* Selector */
.atp-session__select {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 4rem 1rem;
  min-height: 100vh;
}
.atp-session__select-card {
  background: var(--atp-surface);
  border: 1px solid var(--atp-border);
  border-radius: 12px;
  padding: 2.5rem;
  max-width: 680px;
  width: 100%;
}
.atp-session__title { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.25rem; }
.atp-session__subtitle { color: var(--atp-muted); margin-bottom: 2rem; }
.atp-session__scenarios { display: flex; flex-direction: column; gap: 1rem; margin-bottom: 1.5rem; }
.atp-session__scenario-card {
  background: var(--atp-bg);
  border: 1px solid var(--atp-border);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  cursor: pointer;
  transition: border-color 0.15s;
}
.atp-session__scenario-card:hover { border-color: var(--atp-accent); }
.atp-session__scenario-card.selected { border-color: var(--atp-accent); background: #eff6ff; }
.atp-session__scenario-title { font-weight: 600; margin-bottom: 0.35rem; }
.atp-session__scenario-desc { color: var(--atp-muted); font-size: 0.875rem; }
.atp-session__scenario-meta { display: flex; gap: 0.5rem; margin-top: 0.5rem; }

/* Active session */
.atp-session__active {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.atp-session__header {
  padding: 0.75rem 1.5rem;
  background: var(--atp-surface);
  border-bottom: 1px solid var(--atp-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}
.atp-session__scenario-name { font-weight: 600; }
.atp-session__meta { display: flex; align-items: center; gap: 1rem; }
.atp-session__turn-count { color: var(--atp-muted); font-size: 0.875rem; }
.atp-session__competency-bar { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.atp-session__comp-chip {
  position: relative;
  background: var(--atp-border);
  border-radius: 99px;
  padding: 2px 10px;
  font-size: 0.75rem;
  overflow: hidden;
  min-width: 80px;
  text-align: center;
}
.atp-session__comp-label { position: relative; z-index: 1; }
.atp-session__comp-fill {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  background: rgba(99, 102, 241, 0.35);
  transition: width 0.4s ease;
}

.atp-session__affective {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem 1.5rem;
  background: var(--atp-surface);
  border-bottom: 1px solid var(--atp-border);
  flex-shrink: 0;
}
.affective-chip {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--atp-border);
}
.chip--good { background: rgba(34, 197, 94, 0.2); color: var(--atp-good); }
.chip--mid  { background: rgba(245, 158, 11, 0.2); color: var(--atp-mid); }
.chip--bad  { background: rgba(239, 68, 68, 0.2);  color: var(--atp-bad); }
.chip--low  { background: rgba(239, 68, 68, 0.2);  color: var(--atp-bad); }

.atp-session__conversation {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.atp-session__msg { display: flex; }
.atp-session__msg--agent  { justify-content: flex-start; }
.atp-session__msg--learner { justify-content: flex-end; }
.atp-session__msg--system  { justify-content: center; }
.atp-session__msg-bubble {
  max-width: 72%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
}
.atp-session__msg--agent  .atp-session__msg-bubble { background: var(--atp-agent-bg);  border-radius: 4px 12px 12px 12px; }
.atp-session__msg--learner .atp-session__msg-bubble { background: var(--atp-accent);    border-radius: 12px 4px 12px 12px; }
.atp-session__msg--system  .atp-session__msg-bubble { background: transparent; color: var(--atp-muted); font-size: 0.875rem; text-align: center; }
.atp-session__msg-speaker { font-size: 0.75rem; font-weight: 600; color: var(--atp-muted); margin-bottom: 0.25rem; }
.atp-session__nonverbal { font-style: italic; margin-left: 0.5rem; }
.atp-session__msg-text { line-height: 1.55; }
.atp-session__comp-updates { display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap; }
.atp-session__comp-spark {
  font-size: 0.7rem;
  padding: 1px 6px;
  border-radius: 99px;
}
.spark--up   { background: rgba(34,197,94,0.2); color: #22c55e; }
.spark--down { background: rgba(239,68,68,0.2);  color: #ef4444; }
.atp-session__intervention {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(245,158,11,0.1);
  border-left: 3px solid var(--atp-mid);
  border-radius: 0 6px 6px 0;
  font-size: 0.875rem;
}
.atp-session__typing { display: flex; gap: 4px; align-items: center; padding: 0.75rem 1rem; }
.atp-session__typing span {
  width: 7px; height: 7px; background: var(--atp-muted); border-radius: 50%;
  animation: typing-bounce 1.2s infinite;
}
.atp-session__typing span:nth-child(2) { animation-delay: 0.2s; }
.atp-session__typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-4px); opacity: 1; }
}

.atp-session__situation {
  padding: 0.75rem 1.5rem;
  background: rgba(99, 102, 241, 0.08);
  border-top: 1px solid rgba(99,102,241,0.2);
  font-size: 0.875rem;
  color: var(--atp-muted);
  flex-shrink: 0;
}

.atp-session__input-area {
  padding: 1rem 1.5rem;
  background: var(--atp-surface);
  border-top: 1px solid var(--atp-border);
  flex-shrink: 0;
}
.atp-session__textarea {
  width: 100%;
  background: var(--atp-bg);
  border: 1px solid var(--atp-border);
  border-radius: 8px;
  color: var(--atp-text);
  padding: 0.75rem;
  font-size: 0.9375rem;
  font-family: inherit;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}
.atp-session__textarea:focus { border-color: var(--atp-accent); }
.atp-session__input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
}
.atp-session__hint { color: var(--atp-muted); font-size: 0.75rem; }

.atp-session__debrief-prompt {
  padding: 1rem 1.5rem;
  text-align: center;
  flex-shrink: 0;
}

/* Debrief */
.atp-session__debrief {
  max-width: 720px;
  margin: 0 auto;
  padding: 3rem 1.5rem;
}
.atp-session__debrief-title { font-size: 1.75rem; font-weight: 700; margin-bottom: 1.5rem; }
.atp-session__debrief-summary { color: var(--atp-text); line-height: 1.7; margin-bottom: 2rem; }
.atp-session__debrief-section h3 { font-size: 1rem; font-weight: 600; margin-bottom: 0.75rem; color: var(--atp-muted); }
.atp-session__debrief-comp {
  background: var(--atp-surface);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  border-left: 4px solid var(--atp-border);
}
.perf--strong   { border-left-color: var(--atp-good); }
.perf--developing { border-left-color: var(--atp-mid); }
.perf--needs_work { border-left-color: var(--atp-bad); }
.atp-session__debrief-comp-label { font-weight: 600; }
.atp-session__debrief-comp-perf { font-size: 0.75rem; color: var(--atp-muted); margin-left: 0.5rem; }
.atp-session__debrief-comp-note { color: var(--atp-muted); font-size: 0.875rem; margin-top: 0.25rem; }

/* Shared */
.badge {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 99px;
  background: rgba(99,102,241,0.2);
  color: #818cf8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.badge--pair { background: rgba(34,197,94,0.2); color: #22c55e; }

.atp-session__btn {
  padding: 0.6rem 1.5rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9375rem;
  font-weight: 600;
  transition: opacity 0.15s;
}
.atp-session__btn:disabled { opacity: 0.4; cursor: not-allowed; }
.atp-session__btn--primary  { background: var(--atp-accent); color: white; }
.atp-session__btn--secondary { background: var(--atp-border); color: var(--atp-text); }

.atp-session__loading { color: var(--atp-muted); padding: 1rem 0; }
.atp-session__error {
  color: var(--atp-bad);
  font-size: 0.875rem;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(239,68,68,0.08);
  border-radius: 6px;
}
</style>
