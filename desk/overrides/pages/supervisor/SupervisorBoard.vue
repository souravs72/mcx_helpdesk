<template>
  <div class="flex flex-col h-full">
    <LayoutHeader>
      <template #left-header>
        <div class="text-base font-semibold text-ink-gray-9 flex items-center gap-2">
          <LucideRadio class="size-4 text-ink-violet-5" />
          <span>{{ __("Live Queue") }}</span>
          <Badge
            v-if="liveRows.length"
            :label="String(liveRows.length)"
            theme="gray"
            variant="subtle"
          />
        </div>
      </template>
      <template #right-header>
        <div class="flex items-center gap-2">
          <div class="w-44">
            <Autocomplete
              :options="teamOptions"
              :placeholder="__('All Departments')"
              v-model="selectedTeamOption"
            />
          </div>
          <Button
            variant="subtle"
            :icon-left="'lucide-refresh-ccw'"
            :loading="queue.loading"
            @click="queue.reload()"
          />
        </div>
      </template>
    </LayoutHeader>

    <div class="px-5 py-3 border-b border-outline-gray-1 flex flex-wrap gap-2 text-xs">
      <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
        <span class="size-2 rounded-full bg-amber-500" />
        {{ __("Warning") }} ≥ {{ settings.warning_threshold_pct }}%
      </span>
      <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-red-50 text-red-700 border border-red-200">
        <span class="size-2 rounded-full bg-red-500" />
        {{ __("Critical") }} ≥ {{ settings.critical_threshold_pct }}%
      </span>
      <span class="text-ink-gray-5 ml-auto self-center">
        {{ __("Updates every second · refreshes from server every") }}
        {{ settings.supervisor_board_refresh_seconds }}s
      </span>
    </div>

    <div class="flex-1 overflow-auto bg-surface-gray-1 p-5">
      <div v-if="queue.loading && !queue.data" class="flex justify-center py-20">
        <LoadingIndicator :scale="8" />
      </div>

      <div
        v-else-if="!liveRows.length"
        class="rounded-xl border border-outline-gray-1 bg-surface-white p-10 text-center text-ink-gray-5"
      >
        {{ __("No open tickets with active SLA deadlines.") }}
      </div>

      <div v-else class="rounded-xl border border-outline-gray-1 bg-surface-white overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-surface-gray-1 border-b border-outline-gray-1">
            <tr class="text-left text-ink-gray-6">
              <th class="px-4 py-3 font-medium">{{ __("Countdown") }}</th>
              <th class="px-4 py-3 font-medium">{{ __("Ticket") }}</th>
              <th class="px-4 py-3 font-medium">{{ __("Department") }}</th>
              <th class="px-4 py-3 font-medium">{{ __("Priority") }}</th>
              <th class="px-4 py-3 font-medium">{{ __("SLA") }}</th>
              <th class="px-4 py-3 font-medium">{{ __("Risk") }}</th>
              <th class="px-4 py-3 font-medium">{{ __("Assignee") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in liveRows"
              :key="row.name"
              class="border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1 cursor-pointer"
              @click="openTicket(row.name)"
            >
              <td class="px-4 py-3 whitespace-nowrap">
                <div class="font-mono font-semibold tabular-nums" :class="countdownClass(row)">
                  {{ formatCountdown(row.deadline) }}
                </div>
                <div class="text-xs text-ink-gray-5 mt-0.5">{{ row.elapsed_pct }}% {{ __("elapsed") }}</div>
              </td>
              <td class="px-4 py-3">
                <div class="font-medium text-ink-gray-9">#{{ row.name }}</div>
                <div class="text-ink-gray-6 truncate max-w-md">{{ row.subject }}</div>
              </td>
              <td class="px-4 py-3 text-ink-gray-7">{{ row.department || "—" }}</td>
              <td class="px-4 py-3">
                <Badge :label="row.priority || '—'" theme="gray" variant="subtle" />
              </td>
              <td class="px-4 py-3 text-ink-gray-7">{{ row.sla_target }}</td>
              <td class="px-4 py-3">
                <Badge :label="row.risk_level" :theme="riskTheme(row.risk_level)" variant="subtle" />
              </td>
              <td class="px-4 py-3 text-ink-gray-6 text-xs">
                {{ row.assignees?.join(", ") || __("Unassigned") }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import LayoutHeader from "@/components/LayoutHeader.vue";
import { globalStore } from "@/stores/globalStore";
import { __ } from "@/translation";
import {
  Autocomplete,
  Badge,
  Button,
  createResource,
  LoadingIndicator,
} from "frappe-ui";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import LucideRadio from "~icons/lucide/radio";

type QueueRow = {
  name: string;
  subject: string;
  priority: string;
  department: string;
  sla_target: string;
  deadline: string;
  elapsed_pct: number;
  risk_level: string;
  assignees: string[];
};

const router = useRouter();
const { $socket } = globalStore();
const now = ref(Date.now());
const selectedTeamOption = ref<{ label: string; value: string } | null>(null);

const queue = createResource({
  url: "mcx_helpdesk.api.supervisor.get_supervisor_queue",
  makeParams: () => ({
    team: selectedTeamOption.value?.value || null,
  }),
  auto: true,
});

const settings = computed(
  () =>
    queue.data?.settings || {
      warning_threshold_pct: 75,
      critical_threshold_pct: 90,
      supervisor_board_refresh_seconds: 30,
    }
);

const teamOptions = computed(() => {
  const teams = new Set<string>();
  for (const row of queue.data?.tickets || []) {
    if (row.department) teams.add(row.department);
  }
  return [
    { label: __("All Departments"), value: "" },
    ...Array.from(teams)
      .sort()
      .map((t) => ({ label: t, value: t })),
  ];
});

const liveRows = computed<QueueRow[]>(() => {
  const rows: QueueRow[] = queue.data?.tickets || [];
  return rows.map((row) => ({
    ...row,
    risk_level: deriveRisk(row),
  }));
});

let tickTimer: ReturnType<typeof setInterval> | null = null;
let refreshTimer: ReturnType<typeof setInterval> | null = null;

function scheduleRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  const seconds = queue.data?.settings?.supervisor_board_refresh_seconds || 30;
  refreshTimer = setInterval(() => queue.reload(), seconds * 1000);
}

function deriveRisk(row: QueueRow) {
  if (row.risk_level === "Breached") return "Breached";
  const remaining = new Date(row.deadline).getTime() - now.value;
  if (remaining <= 0) return "Breached";
  const pct = row.elapsed_pct ?? 0;
  if (pct >= settings.value.critical_threshold_pct) return "Critical";
  if (pct >= settings.value.warning_threshold_pct) return "Warning";
  return row.risk_level || "None";
}

function remainingMs(deadline: string) {
  return new Date(deadline).getTime() - now.value;
}

function formatCountdown(deadline: string) {
  const ms = remainingMs(deadline);
  if (ms <= 0) return __("BREACHED");

  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function countdownClass(row: QueueRow) {
  const risk = deriveRisk(row);
  if (risk === "Breached") return "text-red-600";
  if (risk === "Critical") return "text-red-500";
  if (risk === "Warning") return "text-amber-600";
  return "text-ink-gray-8";
}

function riskTheme(risk: string) {
  if (risk === "Breached" || risk === "Critical") return "red";
  if (risk === "Warning") return "orange";
  return "gray";
}

function openTicket(name: string) {
  router.push({ name: "TicketAgent", params: { ticketId: name } });
}

watch(selectedTeamOption, () => queue.reload());

watch(
  () => queue.data?.settings?.supervisor_board_refresh_seconds,
  () => scheduleRefresh()
);

onMounted(() => {
  tickTimer = setInterval(() => {
    now.value = Date.now();
  }, 1000);
  scheduleRefresh();

  $socket.on("helpdesk:ticket-update", () => queue.reload());
  $socket.on("helpdesk:new-ticket", () => queue.reload());
});

onUnmounted(() => {
  if (tickTimer) clearInterval(tickTimer);
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>
