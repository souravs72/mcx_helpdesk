<template>
  <div v-if="aiStatus.data?.enabled" class="rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3">
    <div class="flex items-center justify-between gap-2 mb-2">
      <div class="flex items-center gap-2">
        <LucideSparkles class="size-4 text-ink-violet-5" />
        <span class="text-sm font-semibold text-ink-gray-8">{{ __("AI Assist") }}</span>
      </div>
      <div class="flex gap-1">
        <Button
          v-if="aiStatus.data?.suggest_reply"
          size="sm"
          variant="subtle"
          :label="__('Suggest reply')"
          :loading="suggestLoading"
          @click="loadSuggestion"
        />
        <Button
          v-if="aiStatus.data?.summarize_ticket"
          size="sm"
          variant="subtle"
          :label="__('Summarize')"
          :loading="summaryLoading"
          @click="loadSummary"
        />
      </div>
    </div>

    <div v-if="suggestion?.reply" class="space-y-2">
      <p class="text-xs font-medium text-ink-gray-6">{{ __("Suggested reply") }}</p>
      <div class="rounded-md border border-outline-gray-2 bg-surface-white p-2.5 text-sm text-ink-gray-8 whitespace-pre-wrap">
        {{ suggestion.reply }}
      </div>
      <Button size="sm" variant="solid" :label="__('Use in reply')" @click="useSuggestedReply" />
    </div>

    <div v-else-if="summary?.summary" class="space-y-2">
      <p class="text-xs font-medium text-ink-gray-6">{{ __("Summary") }}</p>
      <div class="rounded-md border border-outline-gray-2 bg-surface-white p-2.5 text-sm text-ink-gray-8 whitespace-pre-wrap">
        {{ summary.summary }}
      </div>
      <ul v-if="summary.next_steps?.length" class="text-xs text-ink-gray-6 list-disc pl-4 space-y-1">
        <li v-for="(step, i) in summary.next_steps" :key="i">{{ step }}</li>
      </ul>
    </div>

    <p v-else class="text-xs text-ink-gray-5">
      {{ __("Get AI-generated reply drafts or supervisor summaries for this ticket.") }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { Button, createResource, toast } from "frappe-ui";
import { CommunicationAreaSymbol } from "@/composables/mcxCommunication";
import { inject, ref } from "vue";
import { TicketSymbol } from "@/types";
import { __ } from "@/translation";

const ticket = inject(TicketSymbol)!;
const communicationArea = inject(CommunicationAreaSymbol, null);
const suggestion = ref<{ reply?: string } | null>(null);
const summary = ref<{ summary?: string; next_steps?: string[] } | null>(null);
const suggestLoading = ref(false);
const summaryLoading = ref(false);

const aiStatus = createResource({
  url: "mcx_helpdesk.api.ai.get_ai_status",
  auto: true,
});

async function loadSuggestion() {
  suggestLoading.value = true;
  summary.value = null;
  try {
    const res = await fetch(
      `/api/method/mcx_helpdesk.api.ai.get_suggested_reply?ticket_id=${encodeURIComponent(ticket.value.name)}`,
      { credentials: "include" }
    );
    const data = await res.json();
    if (data.exc) throw new Error(data.exc);
    suggestion.value = data.message;
  } catch (e) {
    console.error(e);
  } finally {
    suggestLoading.value = false;
  }
}

async function loadSummary() {
  summaryLoading.value = true;
  suggestion.value = null;
  try {
    const res = await fetch(
      `/api/method/mcx_helpdesk.api.ai.get_ticket_summary?ticket_id=${encodeURIComponent(ticket.value.name)}`,
      { credentials: "include" }
    );
    const data = await res.json();
    if (data.exc) throw new Error(data.exc);
    summary.value = data.message;
  } catch (e) {
    console.error(e);
  } finally {
    summaryLoading.value = false;
  }
}

function useSuggestedReply() {
  const text = suggestion.value?.reply;
  if (!text) return;

  const area = communicationArea?.value;
  if (area?.insertDraftReply) {
    area.insertDraftReply(text);
    toast.success(__("AI draft inserted into reply editor"));
    return;
  }

  toast.error(__("Open the ticket reply area and try again"));
}
</script>
