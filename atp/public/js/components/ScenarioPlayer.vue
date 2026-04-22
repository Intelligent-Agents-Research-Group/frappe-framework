<script>
import { ref, computed, nextTick, onMounted } from "vue";

const ENGINE_BASE = "http://localhost:8010";

export default {
  name: "ScenarioPlayer",
  props: {
    scenarioId: { type: String, required: true },
    enrollmentName: { type: String, default: null },
  },
  emits: ["complete"],
  setup(props, { emit }) {
    const view = ref("loading"); // loading | session | debrief | error
    const startError = ref(null);

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

    // ── Computed ──────────────────────────────────────────────────────────

    const topCompetencies = computed(() =>
      Object.entries(competencyEstimates.value)
        .slice(0, 4)
        .map(([id, estimate]) => ({ id, label: competencyLabels.value[id] || id, estimate }))
    );

    const engagementClass = computed(() => {
      const e = affectiveState.value?.engagement || 0;
      return e > 0.6 ? "chip--good" : e > 0.3 ? "chip--mid" : "chip--low";
    });

    const frustrationClass = computed(() => {
      const f = affectiveState.value?.frustration || 0;
      return f > 0.7 ? "chip--bad" : f > 0.4 ? "chip--mid" : "chip--good";
    });

    // ── Helpers ───────────────────────────────────────────────────────────

    function pct(v) { return Math.round((v || 0) * 100) + "%"; }

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
        throw new Error(err?.detail || err?.error?.message || `Engine error ${resp.status}`);
      }
      return resp.json();
    }

    function applyLearnerState(state) {
      if (state.competency_estimates) competencyEstimates.value = state.competency_estimates;
      if (state.affective_state) affectiveState.value = state.affective_state;
    }

    async function scrollToBottom() {
      await nextTick();
      if (convEl.value) convEl.value.scrollTop = convEl.value.scrollHeight;
    }

    // ── Session start ─────────────────────────────────────────────────────

    async function startSession() {
      view.value = "loading";
      startError.value = null;
      messages.value = [];
      try {
        // Load scenario title for display
        try {
          const list = await frappeCall("atp.atp.api_v2.get_scenario_list");
          const match = (list || []).find((s) => s.name === props.scenarioId);
          scenarioTitle.value = match?.title || props.scenarioId;
        } catch {
          scenarioTitle.value = props.scenarioId;
        }

        // Create and submit session; engine /session/start is called server-side
        // and the agent's opening utterance is returned alongside session IDs
        const result = await frappeCall("atp.atp.api_v2.create_and_submit_session", {
          scenario_id: props.scenarioId,
        });
        sessionId.value = result.session_id;
        learnerId.value = result.learner_id;

        // Fetch initial learner state from engine
        try {
          const resp = await fetch(`${ENGINE_BASE}/learner/state/${result.session_id}`);
          if (resp.ok) applyLearnerState(await resp.json());
        } catch {}

        view.value = "session";

        // Render the agent's opening utterance — no stale "loading" message
        const openingResponses = result.opening_agent_responses || [];
        if (openingResponses.length > 0) {
          for (const ar of openingResponses) {
            messages.value.push({
              role: "agent",
              speaker: ar.character_id || "Agent",
              text: ar.spoken_text,
              expression: ar.nonverbal_cues?.expression,
              competencyUpdates: [],
              intervention: null,
            });
          }
        }

        await scrollToBottom();
      } catch (e) {
        startError.value = "Could not start scenario: " + (e.message || "unknown error");
        view.value = "error";
      }
    }

    // ── Turn ──────────────────────────────────────────────────────────────

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
        if (resp.competency_updates) {
          for (const u of resp.competency_updates) {
            competencyEstimates.value[u.competency_node_id] = u.new_estimate;
            competencyLabels.value[u.competency_node_id] = u.competency_label;
          }
        }
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
        if (resp.next_step?.situation_text) currentSituationText.value = resp.next_step.situation_text;
        sessionStatus.value = resp.session_status || "in_progress";
        if (resp.session_status !== "debrief_ready") {
          try {
            const state = await fetch(`${ENGINE_BASE}/learner/state/${sessionId.value}`).then((r) => r.json());
            applyLearnerState(state);
          } catch {}
        }
        await scrollToBottom();
      } catch (e) {
        agentTyping.value = false;
        turnError.value = "Error: " + e.message;
      } finally {
        sending.value = false;
      }
    }

    // ── End / debrief ─────────────────────────────────────────────────────

    async function endSession() {
      try {
        const resp = await enginePost("/session/end", {
          session_id: sessionId.value,
          learner_id: learnerId.value,
          end_reason: "completed",
          learner_initiated: true,
        });
        debrief.value = resp.debrief || null;
        view.value = "debrief";
      } catch (e) {
        turnError.value = "Failed to end session: " + e.message;
      }
    }

    function continueFromDebrief() {
      emit("complete");
    }

    onMounted(() => startSession());

    return {
      view, startError,
      scenarioTitle, learnerId, messages, userInput, sending, agentTyping,
      turnCount, sessionStatus, turnError, currentSituationText,
      topCompetencies, affectiveState, engagementClass, frustrationClass,
      debrief, convEl,
      pct, sendTurn, endSession, continueFromDebrief,
    };
  },
};
</script>

<template>
  <div class="sp">

    <!-- Loading -->
    <div v-if="view === 'loading'" class="sp__loading">
      <div class="sp__spinner"></div>
      <span>Starting scenario…</span>
    </div>

    <!-- Error -->
    <div v-else-if="view === 'error'" class="sp__error-state">
      <div class="sp__error-icon">⚠️</div>
      <p class="sp__error-msg">{{ startError }}</p>
      <button class="sp__btn sp__btn--primary" @click="startSession">Retry</button>
    </div>

    <!-- Active session -->
    <div v-else-if="view === 'session'" class="sp__session">

      <!-- Session header -->
      <div class="sp__header">
        <div class="sp__scenario-name">{{ scenarioTitle }}</div>
        <div class="sp__meta">
          <span class="sp__turn-count">Turn {{ turnCount }}</span>
          <div class="sp__comp-bar">
            <div
              v-for="comp in topCompetencies"
              :key="comp.id"
              class="sp__comp-chip"
              :title="comp.label"
            >
              <span class="sp__comp-label">{{ comp.label }}</span>
              <div class="sp__comp-fill" :style="{ width: (comp.estimate * 100) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Affective state -->
      <div v-if="affectiveState" class="sp__affective">
        <span class="sp__chip" :class="engagementClass">Engagement {{ pct(affectiveState.engagement) }}</span>
        <span class="sp__chip" :class="frustrationClass">Frustration {{ pct(affectiveState.frustration) }}</span>
        <span class="sp__chip">Confidence {{ pct(affectiveState.confidence) }}</span>
      </div>

      <!-- Conversation -->
      <div class="sp__conversation" ref="convEl">
        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="sp__msg"
          :class="'sp__msg--' + msg.role"
        >
          <div class="sp__bubble">
            <div v-if="msg.role === 'agent'" class="sp__speaker">
              {{ msg.speaker || 'Agent' }}
              <span v-if="msg.expression" class="sp__nonverbal">[{{ msg.expression }}]</span>
            </div>
            <div class="sp__msg-text">{{ msg.text }}</div>
            <div v-if="msg.competencyUpdates?.length" class="sp__comp-sparks">
              <span
                v-for="u in msg.competencyUpdates"
                :key="u.competency_node_id"
                class="sp__spark"
                :class="u.new_estimate > u.previous_estimate ? 'spark--up' : 'spark--down'"
              >{{ u.competency_label }} {{ u.new_estimate > u.previous_estimate ? '↑' : '↓' }}</span>
            </div>
            <div v-if="msg.intervention" class="sp__intervention">
              💡 {{ msg.intervention.content }}
            </div>
          </div>
        </div>
        <!-- Typing indicator -->
        <div v-if="agentTyping" class="sp__msg sp__msg--agent">
          <div class="sp__bubble sp__typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <!-- Situation context -->
      <div v-if="currentSituationText" class="sp__situation">{{ currentSituationText }}</div>

      <!-- Input area -->
      <div v-if="sessionStatus === 'in_progress'" class="sp__input-area">
        <textarea
          v-model="userInput"
          class="sp__textarea"
          placeholder="Type your response…"
          :disabled="sending"
          rows="3"
          @keydown.ctrl.enter="sendTurn"
          @keydown.meta.enter="sendTurn"
        ></textarea>
        <div class="sp__input-row">
          <span class="sp__hint">Ctrl+Enter to send</span>
          <button
            class="sp__btn sp__btn--primary"
            :disabled="!userInput.trim() || sending"
            @click="sendTurn"
          >{{ sending ? 'Sending…' : 'Send' }}</button>
        </div>
        <div v-if="turnCount >= 1" class="sp__finish-row">
          <button class="sp__btn sp__btn--secondary" @click="endSession" :disabled="sending">
            Finish Scenario
          </button>
        </div>
        <div v-if="turnError" class="sp__turn-error">{{ turnError }}</div>
      </div>

      <!-- Debrief prompt -->
      <div v-if="sessionStatus === 'debrief_ready'" class="sp__debrief-prompt">
        <button class="sp__btn sp__btn--primary" @click="endSession">See Debrief →</button>
      </div>

    </div>

    <!-- Debrief -->
    <div v-else-if="view === 'debrief'" class="sp__debrief">
      <h3 class="sp__debrief-title">Session Debrief</h3>

      <div v-if="debrief">
        <p class="sp__debrief-summary">{{ debrief.summary_text }}</p>

        <div v-if="debrief.competency_highlights?.length" class="sp__debrief-section">
          <div class="sp__debrief-section-label">Competencies</div>
          <div
            v-for="h in debrief.competency_highlights"
            :key="h.competency_label"
            class="sp__debrief-comp"
            :class="'perf--' + h.performance"
          >
            <span class="sp__debrief-comp-label">{{ h.competency_label }}</span>
            <span class="sp__debrief-comp-perf">{{ h.performance }}</span>
            <p class="sp__debrief-comp-note">{{ h.note }}</p>
          </div>
        </div>

        <div v-if="debrief.recommended_focus?.length" class="sp__debrief-section">
          <div class="sp__debrief-section-label">Focus Next</div>
          <ul class="sp__debrief-list">
            <li v-for="f in debrief.recommended_focus" :key="f">{{ f }}</li>
          </ul>
        </div>
      </div>
      <div v-else class="sp__loading">Loading debrief…</div>

      <div class="sp__debrief-footer">
        <button class="sp__btn sp__btn--primary" @click="continueFromDebrief">
          Continue →
        </button>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* ── Theme tokens (light) ─────────────────────────────────────────────── */
.sp {
  --sp-bg: #f9fafb;
  --sp-surface: #ffffff;
  --sp-border: #e5e7eb;
  --sp-text: #111827;
  --sp-muted: #6b7280;
  --sp-accent: #3b82f6;
  --sp-accent-light: #eff6ff;
  --sp-agent-bg: #eff6ff;
  --sp-learner-bg: #f3f4f6;
  --sp-good: #16a34a;
  --sp-mid: #d97706;
  --sp-bad: #dc2626;

  background: var(--sp-bg);
  color: var(--sp-text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  border-radius: 8px;
  border: 1px solid var(--sp-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Loading / error ──────────────────────────────────────────────────── */
.sp__loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 2.5rem;
  color: var(--sp-muted);
  justify-content: center;
}

.sp__spinner {
  width: 22px;
  height: 22px;
  border: 2px solid var(--sp-border);
  border-top-color: var(--sp-accent);
  border-radius: 50%;
  animation: sp-spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes sp-spin { to { transform: rotate(360deg); } }

.sp__error-state {
  text-align: center;
  padding: 3rem 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.sp__error-icon { font-size: 2.5rem; }
.sp__error-msg { color: var(--sp-bad); font-size: 0.875rem; margin: 0; }

/* ── Session layout ───────────────────────────────────────────────────── */
.sp__session {
  display: flex;
  flex-direction: column;
  min-height: 520px;
}

/* ── Header ───────────────────────────────────────────────────────────── */
.sp__header {
  padding: 0.65rem 1rem;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}

.sp__scenario-name { font-weight: 600; font-size: 0.9rem; }
.sp__meta { display: flex; align-items: center; gap: 0.75rem; }
.sp__turn-count { font-size: 0.78rem; opacity: 0.85; }

.sp__comp-bar { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.sp__comp-chip {
  position: relative;
  background: rgba(255,255,255,0.15);
  border-radius: 99px;
  padding: 2px 8px;
  font-size: 0.7rem;
  overflow: hidden;
  min-width: 72px;
  text-align: center;
  color: #fff;
}
.sp__comp-label { position: relative; z-index: 1; }
.sp__comp-fill {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  background: rgba(255,255,255,0.25);
  transition: width 0.4s ease;
}

/* ── Affective ────────────────────────────────────────────────────────── */
.sp__affective {
  display: flex;
  gap: 0.4rem;
  padding: 0.4rem 1rem;
  background: var(--sp-surface);
  border-bottom: 1px solid var(--sp-border);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.sp__chip {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--sp-border);
  color: var(--sp-muted);
}
.chip--good { background: #dcfce7; color: var(--sp-good); }
.chip--mid  { background: #fef3c7; color: var(--sp-mid); }
.chip--bad  { background: #fee2e2; color: var(--sp-bad); }
.chip--low  { background: #fee2e2; color: var(--sp-bad); }

/* ── Conversation ─────────────────────────────────────────────────────── */
.sp__conversation {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 240px;
  max-height: 360px;
  background: var(--sp-bg);
}

.sp__msg { display: flex; }
.sp__msg--agent   { justify-content: flex-start; }
.sp__msg--learner { justify-content: flex-end; }
.sp__msg--system  { justify-content: center; }

.sp__bubble {
  max-width: 75%;
  padding: 0.6rem 0.85rem;
  border-radius: 12px;
  font-size: 0.9rem;
  line-height: 1.5;
}

.sp__msg--agent  .sp__bubble {
  background: var(--sp-surface);
  border: 1px solid var(--sp-border);
  border-radius: 4px 12px 12px 12px;
  color: var(--sp-text);
}

.sp__msg--learner .sp__bubble {
  background: var(--sp-accent);
  border-radius: 12px 4px 12px 12px;
  color: #ffffff;
}

.sp__msg--system .sp__bubble {
  background: transparent;
  color: var(--sp-muted);
  font-size: 0.8rem;
  text-align: center;
  padding: 0.3rem 0;
}

.sp__speaker {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--sp-accent);
  margin-bottom: 0.2rem;
}
.sp__nonverbal { font-style: italic; color: var(--sp-muted); margin-left: 0.35rem; }
.sp__msg-text { line-height: 1.5; }

.sp__comp-sparks { display: flex; gap: 0.35rem; margin-top: 0.4rem; flex-wrap: wrap; }
.sp__spark { font-size: 0.68rem; padding: 1px 5px; border-radius: 99px; }
.spark--up   { background: #dcfce7; color: #16a34a; }
.spark--down { background: #fee2e2; color: #dc2626; }

.sp__intervention {
  margin-top: 0.4rem;
  padding: 0.4rem 0.6rem;
  background: #fef3c7;
  border-left: 3px solid var(--sp-mid);
  border-radius: 0 5px 5px 0;
  font-size: 0.82rem;
  color: #92400e;
}

.sp__typing { display: flex; gap: 4px; align-items: center; }
.sp__typing span {
  width: 6px; height: 6px;
  background: var(--sp-muted);
  border-radius: 50%;
  animation: sp-bounce 1.2s infinite;
}
.sp__typing span:nth-child(2) { animation-delay: 0.2s; }
.sp__typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes sp-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-4px); opacity: 1; }
}

/* ── Situation ────────────────────────────────────────────────────────── */
.sp__situation {
  padding: 0.6rem 1rem;
  background: var(--sp-accent-light);
  border-top: 1px solid #bfdbfe;
  font-size: 0.82rem;
  color: #1d4ed8;
  flex-shrink: 0;
}

/* ── Input ────────────────────────────────────────────────────────────── */
.sp__input-area {
  padding: 0.75rem 1rem;
  background: var(--sp-surface);
  border-top: 1px solid var(--sp-border);
  flex-shrink: 0;
}

.sp__textarea {
  width: 100%;
  background: var(--sp-bg);
  border: 1px solid var(--sp-border);
  border-radius: 6px;
  color: var(--sp-text);
  padding: 0.6rem 0.75rem;
  font-size: 0.875rem;
  font-family: inherit;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}

.sp__textarea:focus {
  border-color: var(--sp-accent);
  box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
}

.sp__input-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.4rem;
}

.sp__hint { color: var(--sp-muted); font-size: 0.72rem; }

.sp__turn-error {
  margin-top: 0.4rem;
  color: var(--sp-bad);
  font-size: 0.8rem;
  padding: 0.35rem 0.6rem;
  background: #fee2e2;
  border-radius: 5px;
}

.sp__finish-row {
  margin-top: 0.5rem;
  text-align: right;
}

.sp__btn--secondary {
  background: var(--sp-surface);
  color: var(--sp-muted);
  border: 1px solid var(--sp-border);
}
.sp__btn--secondary:hover:not(:disabled) {
  background: var(--sp-border);
  color: var(--sp-text);
}

.sp__debrief-prompt {
  padding: 0.75rem 1rem;
  text-align: center;
  border-top: 1px solid var(--sp-border);
  background: var(--sp-surface);
  flex-shrink: 0;
}

/* ── Debrief ──────────────────────────────────────────────────────────── */
.sp__debrief {
  padding: 1.5rem;
  background: var(--sp-bg);
}

.sp__debrief-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--sp-text);
  margin: 0 0 1rem;
}

.sp__debrief-summary {
  color: var(--sp-text);
  line-height: 1.65;
  margin-bottom: 1.25rem;
  font-size: 0.9rem;
}

.sp__debrief-section { margin-bottom: 1.25rem; }

.sp__debrief-section-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--sp-muted);
  margin-bottom: 0.6rem;
}

.sp__debrief-comp {
  background: var(--sp-surface);
  border: 1px solid var(--sp-border);
  border-radius: 6px;
  padding: 0.6rem 0.85rem;
  margin-bottom: 0.4rem;
  border-left: 4px solid var(--sp-border);
}
.perf--strong      { border-left-color: #16a34a; }
.perf--developing  { border-left-color: #d97706; }
.perf--needs_work  { border-left-color: #dc2626; }

.sp__debrief-comp-label { font-weight: 600; font-size: 0.875rem; }
.sp__debrief-comp-perf  { font-size: 0.72rem; color: var(--sp-muted); margin-left: 0.4rem; }
.sp__debrief-comp-note  { color: var(--sp-muted); font-size: 0.82rem; margin: 0.2rem 0 0; }

.sp__debrief-list { margin: 0; padding-left: 1.25rem; }
.sp__debrief-list li { font-size: 0.875rem; color: var(--sp-text); margin-bottom: 0.3rem; }

.sp__debrief-footer {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--sp-border);
  text-align: right;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
.sp__btn {
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  transition: background 0.15s;
}
.sp__btn:disabled { opacity: 0.45; cursor: not-allowed; }
.sp__btn--primary  { background: var(--sp-accent); color: #ffffff; }
.sp__btn--primary:hover:not(:disabled) { background: #2563eb; }
</style>
