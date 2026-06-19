<template>
  <Teleport to="body">
    <div v-if="showOnPage" class="mcx-chatbot">
      <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-3 scale-95"
        enter-to-class="opacity-100 translate-y-0 scale-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100 translate-y-0 scale-100"
        leave-to-class="opacity-0 translate-y-3 scale-95"
      >
        <div v-if="open" class="chat-panel pointer-events-auto flex flex-col">

          <!-- Header -->
          <div class="chat-header flex items-center justify-between gap-3 px-4 py-3">
            <div class="flex items-center gap-2.5">
              <div class="bot-avatar flex shrink-0 items-center justify-center">
                <LucideSparkles class="size-3.5" style="color:#fff" />
              </div>
              <div>
                <div class="flex items-center gap-1.5">
                  <span class="chat-title">{{ __("FAQ Assistant") }}</span>
                  <span v-if="config.data?.ai_mode" class="ai-badge">AI</span>
                </div>
                <p class="chat-subtitle">
                  {{ config.data?.ai_mode ? __("AI-powered · MCX knowledge base") : __("MCX knowledge base") }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-0.5">
              <button
                v-if="hasUserMessage"
                type="button"
                class="hdr-action flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium transition"
                @click="resetChat"
              >
                <LucideRotateCcw class="size-3" />
                {{ __("New") }}
              </button>
              <button
                type="button"
                class="hdr-action flex items-center justify-center rounded p-1.5 transition"
                :aria-label="__('Close')"
                @click="open = false"
              >
                <LucideX class="size-3.5" />
              </button>
            </div>
          </div>

          <!-- Messages -->
          <div ref="messagesEl" class="chat-messages flex flex-col gap-3 px-3 py-3">

            <template v-for="(msg, index) in messages" :key="index">

              <!-- Bot -->
              <div v-if="msg.role === 'assistant'" class="chat-msg flex items-end gap-2">
                <div class="bot-icon flex shrink-0 items-center justify-center">
                  <LucideSparkles class="size-2.5" style="color:#fff" />
                </div>
                <div class="bot-bubble">
                  <!-- eslint-disable-next-line vue/no-v-html -->
                  <div class="msg-body" v-html="formatContent(msg.content)" />
                </div>
              </div>

              <!-- User -->
              <div v-else class="chat-msg flex items-end justify-end gap-2">
                <div class="user-bubble">{{ msg.content }}</div>
                <div class="user-icon flex shrink-0 items-center justify-center">
                  <LucideUser class="size-3" style="color:#fff" />
                </div>
              </div>

            </template>

            <!-- Suggested questions -->
            <div v-if="!hasUserMessage && suggestedQuestions.length" class="flex flex-col gap-1 pl-7">
              <p class="section-label">{{ __("Suggested questions") }}</p>
              <button
                v-for="q in suggestedQuestions.slice(0, 4)"
                :key="q"
                type="button"
                class="suggestion flex items-center gap-2 rounded-md px-2.5 py-2 text-left text-[12.5px] leading-snug transition"
                @click="askQuestion(q)"
              >
                <LucideChevronRight class="size-3 shrink-0" style="color:rgb(104 70 227)" />
                {{ q }}
              </button>
            </div>

            <!-- Typing -->
            <div v-if="loading" class="chat-msg flex items-end gap-2">
              <div class="bot-icon flex shrink-0 items-center justify-center">
                <LucideSparkles class="size-2.5" style="color:#fff" />
              </div>
              <div class="bot-bubble typing-dots">
                <span class="dot" /><span class="dot" /><span class="dot" />
              </div>
            </div>

            <!-- Sources -->
            <div v-if="lastSources.length" class="flex flex-col gap-1.5 pl-7">
              <p class="section-label">{{ __("Sources") }}</p>
              <div class="flex flex-wrap gap-1.5">
                <RouterLink
                  v-for="s in lastSources"
                  :key="s.name"
                  :to="{ name: 'ArticlePublic', params: { articleId: s.name } }"
                  class="source-chip flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11.5px] font-medium transition"
                  @click="open = false"
                >
                  <LucideBookOpen class="size-3 shrink-0" />
                  <span style="max-width:13rem" class="truncate">{{ s.title }}</span>
                </RouterLink>
              </div>
            </div>

            <!-- Ticket card -->
            <div v-if="suggestTicket" class="ticket-card flex items-start gap-2.5 rounded-lg border px-3.5 py-3">
              <LucideLifeBuoy class="mt-px size-3.5 shrink-0" style="color:rgb(219 119 6)" />
              <div class="flex flex-col gap-1.5">
                <p class="text-[12.5px] font-semibold" style="color:var(--text-ink-gray-9)">
                  {{ __("Need more help?") }}
                </p>
                <p class="text-xs leading-relaxed" style="color:var(--text-ink-gray-6)">
                  {{ __("Our support team can look into your account or ticket directly.") }}
                </p>
                <RouterLink
                  :to="{ name: 'TicketNew' }"
                  class="ticket-btn inline-flex w-fit items-center gap-1 rounded px-2.5 py-1.5 text-xs font-medium transition"
                  @click="open = false"
                >
                  <LucidePlus class="size-3" />
                  {{ __("Create a support ticket") }}
                </RouterLink>
              </div>
            </div>

          </div>

          <!-- Input -->
          <div class="chat-footer px-3 pb-3 pt-2">
            <form
              class="input-row flex items-end gap-2 rounded-md px-3 py-2 transition"
              @submit.prevent="submitQuestion"
            >
              <Textarea
                v-model="input"
                :placeholder="__('Ask about tickets, trading, settlement…')"
                class="input-field flex-1 resize-none bg-transparent text-[13px] outline-none"
                :rows="1"
                :disabled="chatbotDisabled"
                @keydown.enter.exact.prevent="submitQuestion"
              />
              <button
                type="submit"
                class="send-btn flex shrink-0 items-center justify-center rounded"
                :disabled="chatbotDisabled || !input.trim() || loading"
                :aria-label="__('Send')"
              >
                <LucideSend class="size-3.5" style="color:#fff" />
              </button>
            </form>
            <p class="footer-note text-center">
              {{ config.data?.ai_mode ? __("Answers grounded in MCX knowledge base") : __("MCX knowledge base") }}
            </p>
          </div>

        </div>
      </Transition>

      <!-- FAB -->
      <button
        type="button"
        class="chat-fab pointer-events-auto flex items-center justify-center"
        :aria-label="open ? __('Close FAQ assistant') : __('Open FAQ assistant')"
        @click="toggleOpen"
      >
        <Transition
          enter-active-class="transition duration-150"
          enter-from-class="opacity-0 rotate-90 scale-50"
          enter-to-class="opacity-100 rotate-0 scale-100"
          leave-active-class="transition duration-100"
          leave-from-class="opacity-100 rotate-0 scale-100"
          leave-to-class="opacity-0 -rotate-90 scale-50"
          mode="out-in"
        >
          <LucideX v-if="open" class="size-5" style="color:#fff" />
          <LucideMessageCircle v-else class="size-5" style="color:#fff" />
        </Transition>
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { Textarea, createResource } from "frappe-ui";
import LucideBookOpen from "~icons/lucide/book-open";
import LucideChevronRight from "~icons/lucide/chevron-right";
import LucideLifeBuoy from "~icons/lucide/life-buoy";
import LucideMessageCircle from "~icons/lucide/message-circle";
import LucidePlus from "~icons/lucide/plus";
import LucideRotateCcw from "~icons/lucide/rotate-ccw";
import LucideSend from "~icons/lucide/send";
import LucideSparkles from "~icons/lucide/sparkles";
import LucideUser from "~icons/lucide/user";
import LucideX from "~icons/lucide/x";
import { computed, nextTick, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { __ } from "@/translation";
import { isCustomerPortal } from "@/utils";

type ChatMessage = { role: "user" | "assistant"; content: string };
type ArticleSource = { name: string; title: string };

const route = useRoute();
const open = ref(false);
const input = ref("");
const loading = ref(false);
const messages = ref<ChatMessage[]>([]);
const lastSources = ref<ArticleSource[]>([]);
const suggestTicket = ref(false);
const messagesEl = ref<HTMLElement | null>(null);

const showOnPage = computed(() => Boolean(route.meta.public || isCustomerPortal.value));
const chatbotDisabled = computed(() => config.data?.enabled === false);
const suggestedQuestions = computed(() => config.data?.suggested_questions || []);
const hasUserMessage = computed(() => messages.value.some((m) => m.role === "user"));

const config = createResource({
  url: "mcx_helpdesk.api.chatbot.get_config",
  auto: true,
});

/**
 * Sanitise and format bot message content for v-html rendering.
 *
 * Processes text in one pass, grouping lines into chunks:
 *   • Consecutive pipe-delimited lines  → proper HTML <table>
 *   • Short capitalised labels          → .content-heading span
 *   • Numbered list items               → .list-num styled prefix
 *   • Bold / italic markdown            → <strong> / <em>
 *   • Blank lines / newlines            → <br> spacing
 */
function formatContent(raw: string): string {
  // 1. Escape HTML entities in the raw string
  const safe = raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const lines = safe.split("\n");

  type Chunk = { kind: "table"; rows: string[][] } | { kind: "text"; lines: string[] };
  const chunks: Chunk[] = [];

  // 2. Group lines into table-blocks vs text-blocks
  const isTableRow = (s: string) =>
    s.split("|").map((c) => c.trim()).filter((c) => c !== "").length >= 2;

  let i = 0;
  while (i < lines.length) {
    const t = lines[i].trim();
    if (isTableRow(t)) {
      // Collect consecutive pipe-rows (skip blank separators between them)
      const tableLines: string[] = [];
      while (i < lines.length) {
        const cur = lines[i].trim();
        if (isTableRow(cur)) {
          tableLines.push(cur);
          i++;
        } else if (cur === "" && tableLines.length) {
          i++;
          break;
        } else {
          break;
        }
      }
      const rows = tableLines.map((r) =>
        r.split("|").map((c) => c.trim()).filter((c) => c !== "")
      );
      if (rows.length) chunks.push({ kind: "table", rows });
    } else {
      const last = chunks[chunks.length - 1];
      if (!last || last.kind !== "text") {
        chunks.push({ kind: "text", lines: [] });
      }
      (chunks[chunks.length - 1] as { kind: "text"; lines: string[] }).lines.push(lines[i]);
      i++;
    }
  }

  // 3. Render each chunk
  const parts: string[] = [];

  for (const [chunkIdx, chunk] of chunks.entries()) {
    if (chunk.kind === "table") {
      let html = '<div class="tbl-wrap"><table class="content-table">';
      chunk.rows.forEach((cells, idx) => {
        const tag = idx === 0 ? "th" : "td";
        html += "<tr>" + cells.map((c) => `<${tag}>${c}</${tag}>`).join("") + "</tr>";
      });
      html += "</table></div>";
      parts.push(html);
      continue;
    }

    // Text block — heading detection + inline transforms
    const prevChunkIsTable = chunkIdx > 0 && chunks[chunkIdx - 1].kind === "table";
    const textLines = chunk.lines;
    const processed: string[] = [];

    for (let j = 0; j < textLines.length; j++) {
      const line = textLines[j];
      const trimmed = line.trim();
      const prev = j > 0 ? textLines[j - 1].trim() : "";
      // j===0 counts as "top" only when this chunk doesn't immediately follow a table
      const isTopOrAfterBlank = (j === 0 && !prevChunkIsTable) || prev === "";

      const looksLikeHeading =
        isTopOrAfterBlank &&
        trimmed.length >= 3 &&
        trimmed.length <= 55 &&
        /^[A-Z]/.test(trimmed) &&
        !trimmed.includes("|") &&
        !trimmed.startsWith("•") &&
        !/[.,;?!]$/.test(trimmed) &&
        !/^\d+\./.test(trimmed);

      if (looksLikeHeading) {
        processed.push(`<span class="content-heading">${trimmed}</span>`);
      } else {
        processed.push(line);
      }
    }

    const text = processed
      .join("\n")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/^(\d+)\. /gm, '<span class="list-num">$1.</span> ')
      .replace(/\n\n/g, "<br><br>")
      .replace(/\n/g, "<br>");

    if (text.trim()) parts.push(text);
  }

  return parts.join("");
}

const defaultWelcome = () =>
  config.data?.welcome_message ||
  __("Hi! I can help with questions about your tickets, trading, clearing & settlement, and MCX portal access.");

watch(open, async (isOpen) => {
  if (!isOpen || messages.value.length) return;
  messages.value.push({ role: "assistant", content: defaultWelcome() });
  await scrollToBottom();
});

function toggleOpen() {
  if (chatbotDisabled.value) return;
  open.value = !open.value;
}

function resetChat() {
  messages.value = [];
  lastSources.value = [];
  suggestTicket.value = false;
  input.value = "";
  messages.value.push({ role: "assistant", content: defaultWelcome() });
}

async function scrollToBottom() {
  await nextTick();
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
}

async function askQuestion(q: string) {
  input.value = q;
  await submitQuestion();
}

async function submitQuestion() {
  if (chatbotDisabled.value) return;
  const text = input.value.trim();
  if (!text || loading.value) return;

  messages.value.push({ role: "user", content: text });
  input.value = "";
  loading.value = true;
  lastSources.value = [];
  suggestTicket.value = false;
  await scrollToBottom();

  try {
    const history = messages.value
      .slice(0, -1)
      .map((m) => ({ role: m.role, content: m.content }));
    const body = new URLSearchParams({
      message: text,
      history: JSON.stringify(history),
    });
    const res = await fetch("/api/method/mcx_helpdesk.api.chatbot.ask", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    const data = await res.json();
    if (data.exc) throw new Error(data.exc);
    const result = data.message || {};
    messages.value.push({
      role: "assistant",
      content:
        result.answer ||
        __("I couldn't find a clear answer. Please try rephrasing or raise a support ticket."),
    });
    lastSources.value = result.sources || [];
    suggestTicket.value = Boolean(result.suggest_ticket);
  } catch {
    messages.value.push({
      role: "assistant",
      content: __("Something went wrong. Please try again or create a support ticket."),
    });
    suggestTicket.value = true;
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
}
</script>

<style scoped>
/* ─── Positioning (bypasses Tailwind scan) ──────────────────────── */
.mcx-chatbot {
  position: fixed;
  bottom: 5rem;
  right: 1.25rem;
  z-index: 10050;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
  pointer-events: none;
}

/* ─── Panel ─────────────────────────────────────────────────────── */
.chat-panel {
  width: min(100vw - 2rem, 23.5rem);
  background: var(--surface-white);
  border: 1px solid var(--outline-gray-2);
  border-radius: 0.625rem;
  box-shadow:
    0 2px 6px rgb(0 0 0 / 0.06),
    0 8px 24px rgb(0 0 0 / 0.1);
  overflow: hidden;
}

/* ─── Header ────────────────────────────────────────────────────── */
.chat-header {
  /* Frappe violet-500 — flat, no gradient, consistent with Espresso */
  background: rgb(104 70 227);
}

.bot-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: rgb(255 255 255 / 0.18);
  border: 1px solid rgb(255 255 255 / 0.28);
  flex-shrink: 0;
}

.chat-title {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  letter-spacing: -0.01em;
}

.chat-subtitle {
  font-size: 11px;
  color: rgb(255 255 255 / 0.62);
  line-height: 1.3;
}

.ai-badge {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 1px 5px;
  border-radius: 99px;
  background: rgb(255 255 255 / 0.2);
  color: #fff;
  border: 1px solid rgb(255 255 255 / 0.25);
}

.hdr-action {
  color: rgb(255 255 255 / 0.72);
}
.hdr-action:hover {
  background: rgb(255 255 255 / 0.14);
  color: #fff;
}

/* ─── Messages area ─────────────────────────────────────────────── */
.chat-messages {
  background: var(--surface-gray-1);
  min-height: 13rem;
  max-height: 21rem;
  overflow-y: auto;
  /* hide scrollbar — Frappe uses .hide-scrollbar the same way */
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.chat-messages::-webkit-scrollbar { display: none; }

@keyframes msg-slide-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.chat-msg { animation: msg-slide-in 0.18s ease-out both; }

/* ─── Bot icon ──────────────────────────────────────────────────── */
.bot-icon {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: rgb(104 70 227);
  flex-shrink: 0;
  align-self: flex-end;
  margin-bottom: 1px;
}

/* ─── Bot bubble ────────────────────────────────────────────────── */
.bot-bubble {
  background: var(--surface-white);
  border: 1px solid var(--outline-gray-2);
  border-radius: 0.5rem 0.5rem 0.5rem 0.125rem;
  padding: 0.5625rem 0.75rem;
  max-width: calc(100% - 2.75rem);
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.05);
}

.msg-body {
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-ink-gray-8);
}

/* Heading detected inside bot response */
.msg-body :deep(.content-heading) {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgb(104 70 227);
  margin-bottom: 0.3125rem;
  margin-top: 0.125rem;
}
/* Remove top margin for the very first heading */
.msg-body :deep(.content-heading:first-child) { margin-top: 0; }

.msg-body :deep(strong) { font-weight: 600; color: var(--text-ink-gray-9); }
.msg-body :deep(em)     { font-style: italic; color: var(--text-ink-gray-7); }
.msg-body :deep(.list-num) {
  font-weight: 700;
  color: rgb(104 70 227);
  margin-right: 1px;
}
/* ── Inline table rendered from pipe-delimited article content ──── */
.msg-body :deep(.tbl-wrap) {
  overflow-x: auto;
  margin: 0.375rem 0;
  border-radius: 0.375rem;
  border: 1px solid var(--outline-gray-2);
}
.msg-body :deep(.content-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.msg-body :deep(.content-table th) {
  background: var(--surface-gray-2);
  color: var(--text-ink-gray-9);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.3125rem 0.625rem;
  text-align: left;
  border-bottom: 1px solid var(--outline-gray-2);
  white-space: nowrap;
}
.msg-body :deep(.content-table td) {
  color: var(--text-ink-gray-8);
  padding: 0.3125rem 0.625rem;
  border-bottom: 1px solid var(--outline-gray-1);
  vertical-align: top;
  line-height: 1.5;
}
.msg-body :deep(.content-table tr:last-child td) {
  border-bottom: none;
}

/* ─── User icon ─────────────────────────────────────────────────── */
.user-icon {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: rgb(82 56 182); /* slightly darker violet for contrast */
  flex-shrink: 0;
  align-self: flex-end;
  margin-bottom: 1px;
}

/* ─── User bubble ───────────────────────────────────────────────── */
.user-bubble {
  background: rgb(104 70 227);
  border-radius: 0.5rem 0.5rem 0.125rem 0.5rem;
  padding: 0.5625rem 0.75rem;
  font-size: 13px;
  line-height: 1.55;
  color: #fff;
  max-width: calc(100% - 2.75rem);
}

/* ─── Typing dots ───────────────────────────────────────────────── */
.typing-dots {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0.4375rem 0.75rem;
}
.dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--outline-gray-4);
  animation: dot-bounce 1.3s ease-in-out infinite;
}
.dot:nth-child(2) { animation-delay: 0.18s; }
.dot:nth-child(3) { animation-delay: 0.36s; }
@keyframes dot-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-5px); opacity: 1; }
}

/* ─── Section labels ────────────────────────────────────────────── */
.section-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-ink-gray-5);
  padding: 0 0.125rem;
}

/* ─── Suggested questions ───────────────────────────────────────── */
.suggestion {
  background: var(--surface-white);
  border: 1px solid var(--outline-gray-2);
  color: var(--text-ink-gray-8);
}
.suggestion:hover {
  background: var(--surface-violet-1);
  border-color: rgb(104 70 227 / 0.3);
  color: var(--text-ink-gray-9);
}

/* ─── Sources ───────────────────────────────────────────────────── */
.source-chip {
  background: var(--surface-violet-1);
  color: rgb(104 70 227);
  border: 1px solid rgb(104 70 227 / 0.2);
}
.source-chip:hover {
  background: rgb(104 70 227 / 0.12);
  border-color: rgb(104 70 227 / 0.4);
}

/* ─── Ticket card ───────────────────────────────────────────────── */
.ticket-card {
  background: var(--surface-amber-1);
  border-color: var(--outline-amber-1);
  margin-left: 2.25rem;
}
.ticket-btn {
  background: rgb(231 153 19 / 0.12);
  color: rgb(179 83 9);
  border: 1px solid rgb(231 153 19 / 0.4);
}
.ticket-btn:hover { background: rgb(231 153 19 / 0.2); }

/* ─── Footer / Input ────────────────────────────────────────────── */
.chat-footer {
  background: var(--surface-white);
  border-top: 1px solid var(--outline-gray-2);
}

/* Matches Frappe's text input style exactly */
.input-row {
  background: var(--surface-gray-2);
  border: 1px solid var(--outline-gray-2);
}
.input-row:focus-within {
  background: var(--surface-white);
  border-color: rgb(104 70 227 / 0.5);
  box-shadow: 0 0 0 2px rgb(104 70 227 / 0.08);
}

.input-field {
  color: var(--text-ink-gray-8);
  min-height: 1.75rem;
  max-height: 4.5rem;
  font-family: inherit;
}
.input-field::placeholder { color: var(--text-ink-gray-4); }

/* frappe-ui Textarea inner element reset */
:deep(.input-row .form-control) {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
  font-size: 13px;
  color: var(--text-ink-gray-8);
  font-family: inherit;
}

.send-btn {
  width: 1.875rem;
  height: 1.875rem;
  background: rgb(104 70 227);
  border-radius: 0.375rem;
  flex-shrink: 0;
  transition: opacity 0.12s;
}
.send-btn:hover:not(:disabled) { opacity: 0.85; }
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.footer-note {
  margin-top: 0.375rem;
  font-size: 10.5px;
  color: var(--text-ink-gray-4);
}

/* ─── FAB ───────────────────────────────────────────────────────── */
.chat-fab {
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  background: rgb(104 70 227);
  box-shadow: 0 4px 16px rgb(104 70 227 / 0.4);
  pointer-events: auto;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.chat-fab:hover {
  transform: scale(1.06) translateY(-1px);
  box-shadow: 0 6px 20px rgb(104 70 227 / 0.5);
}
.chat-fab:active { transform: scale(0.95); }
</style>
