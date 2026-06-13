<template>
  <div class="flex flex-col h-full">
    <LayoutHeader>
      <template #left-header>
        <div class="text-base font-semibold text-ink-gray-9 flex items-center gap-2">
          <span>{{ __(pageTitle) }}</span>
        </div>
      </template>
      <template #right-header>
        <TabButtons v-if="isManager" v-model="activeTab" :buttons="tabButtons" />
      </template>
    </LayoutHeader>

    <div class="px-5 pt-4 pb-1 border-b border-outline-gray-1 flex flex-wrap items-center gap-2">
      <!-- Date preset -->
      <Dropdown v-if="!showDatePicker" :options="dateOptions" class="!form-control !w-44">
        <template #default>
          <div class="flex justify-between items-center border border-outline-gray-2 rounded text-ink-gray-8 px-2 py-1.5 hover:border-outline-gray-3 hover:shadow-sm h-7 cursor-pointer">
            <div class="flex items-center gap-1.5">
              <LucideCalendar class="size-3.5 text-ink-gray-5" />
              <span class="text-sm whitespace-nowrap">{{ preset }}</span>
            </div>
            <LucideChevronDown class="size-3.5 text-ink-gray-4" />
          </div>
        </template>
      </Dropdown>
      <DateRangePicker v-else class="!w-44" ref="datePickerRef" v-model="periodRange"
        variant="outline" :placeholder="__('Period')" :format="'MMM D'">
        <template #prefix><LucideCalendar class="size-3.5 text-ink-gray-5 me-1" /></template>
      </DateRangePicker>

      <!-- Department -->
      <div v-if="isManager" class="w-44">
        <Autocomplete :options="teamList.data || []" :placeholder="__('All Departments')" v-model="selectedTeamOption" />
      </div>

      <!-- Agent (By Agent tab only) -->
      <div v-if="isManager && activeTab === 'agent'" class="w-52">
        <Autocomplete :options="agentList.data || []" :placeholder="agentListPlaceholder" v-model="selectedAgentOption" />
      </div>

      <button
        v-if="isManager && activeTab === 'agent' && selectedAgent"
        class="text-xs text-ink-gray-5 hover:text-ink-gray-8 flex items-center gap-1"
        @click="selectedAgent = null"
      >
        <LucideChevronLeft class="size-3.5" /> {{ __("All agents") }}
      </button>
    </div>

    <div class="p-5 flex-1 overflow-y-auto bg-surface-gray-1">

      <!-- AGENT SELF-VIEW -->
      <template v-if="!isManager">
        <div class="mb-4">
          <KpiGroupLabel :label="periodLabel" />
          <AgentPeriodKpis :stats="agentStats.data" :loading="agentStats.loading" />
        </div>

        <ActionTicketsPanel
          v-model:active-list="agentActionTab"
          :list-types="agentActionTypes"
          :team="null"
          class="mb-4"
        />

        <div class="mb-4">
          <AgentAnalyticsSection :stats="agentStats.data" :loading="agentStats.loading" />
        </div>
      </template>

      <!-- MANAGER — OVERVIEW -->
      <template v-else-if="activeTab === 'overview'">
        <div class="mb-4">
          <KpiGroupLabel :label="periodLabel" />
          <div v-if="numberCards.loading" class="flex w-full gap-2.5">
            <div v-for="n in 4" :key="n" class="flex-1 h-[88px] rounded-xl bg-surface-white animate-pulse border border-outline-gray-1" />
          </div>
          <KpiStrip v-else :cards="managerPeriodCards" />
        </div>

        <div v-if="trendData.loading || visibleTrendCharts.length || masterData.loading || visibleMasterCharts.length" class="mb-4">
          <div v-if="trendData.loading || visibleTrendCharts.length" class="grid grid-cols-1 gap-4 mb-4">
            <ChartCard v-for="(chart, i) in visibleTrendCharts" :key="'t'+i" :chart="chart" />
            <SkeletonLoader v-if="trendData.loading" :variants="['bar-chart']" :bar-chart-count="1" :loading="true" />
          </div>

          <div v-if="masterData.loading || visibleMasterCharts.length" class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ChartCard
              v-for="(chart, i) in visibleMasterCharts"
              :key="'m'+i"
              :chart="chart"
              :class="masterChartSpanClass(chart)"
            />
            <SkeletonLoader v-if="masterData.loading" :variants="['bar-chart']" :bar-chart-count="2" :loading="true" />
          </div>
        </div>

        <ActionTicketsPanel
          v-model:active-list="managerActionTab"
          :list-types="managerActionTypes"
          :team="filters.team"
          class="mb-4"
        />

        <LeaderboardTable
          :rows="leaderboardRows"
          :loading="leaderboard.loading"
          :clickable="true"
          :title="__('Agents')"
          :total-count="leaderboardTotalCount"
          :page-length="leaderboardPageLength"
          @update:page-length="handleLeaderboardPageLength"
          @load-more="() => handleLeaderboardPageLength(leaderboardPageLength, true)"
          @select-agent="drillToAgent"
          class="mb-4"
        />
      </template>

      <!-- MANAGER — BY AGENT -->
      <template v-else-if="activeTab === 'agent'">
        <template v-if="!selectedAgent">
          <div v-if="managerPeriodCards.length || numberCards.loading" class="mb-4">
            <KpiGroupLabel :label="periodLabel" />
            <div v-if="numberCards.loading" class="flex w-full gap-2.5">
              <div v-for="n in 4" :key="n" class="flex-1 h-20 rounded-xl bg-surface-white animate-pulse border border-outline-gray-1" />
            </div>
            <KpiStrip v-else :cards="managerPeriodCards" />
          </div>
          <div v-if="filters.team" class="mb-3 flex items-center gap-2 text-sm text-ink-gray-6 bg-surface-white rounded-lg px-4 py-2.5 border border-outline-gray-1">
            <LucideBuilding2 class="size-4 text-blue-500" />
            <span>{{ __("Showing agents in") }} <strong class="text-ink-gray-8">{{ filters.team }}</strong></span>
          </div>
          <LeaderboardTable
            :rows="leaderboardRows"
            :loading="leaderboard.loading"
            :clickable="true"
            :title="__('Agents')"
            :total-count="leaderboardTotalCount"
            :page-length="leaderboardPageLength"
            @update:page-length="handleLeaderboardPageLength"
            @load-more="() => handleLeaderboardPageLength(leaderboardPageLength, true)"
            @select-agent="drillToAgent"
          />
        </template>
        <template v-else>
          <div class="mb-4">
            <KpiGroupLabel :label="periodLabel" />
            <AgentPeriodKpis :stats="agentStats.data" :loading="agentStats.loading" />
          </div>
          <div class="mb-4">
            <AgentAnalyticsSection :stats="agentStats.data" :loading="agentStats.loading" />
          </div>
          <ActionTicketsPanel
            v-model:active-list="agentActionTab"
            :list-types="agentDrilldownActionTypes"
            :agent-email="selectedAgent"
            class="mb-4"
          />
        </template>
      </template>

      <!-- MANAGER — BY DEPARTMENT -->
      <template v-else-if="activeTab === 'dept'">
        <div class="mb-4">
          <KpiGroupLabel :label="periodLabel" />
          <div v-if="!deptStats.loading && deptBarChart" class="mb-4">
            <ChartCard :chart="deptBarChart" />
          </div>
          <SkeletonLoader v-if="deptStats.loading" :variants="['bar-chart']" :bar-chart-count="1" :loading="true" class="mb-4" />
          <DeptTable
            :rows="deptRows"
            :loading="deptStats.loading"
            :total-count="deptTotalCount"
            :page-length="deptPageLength"
            @update:page-length="handleDeptPageLength"
            @load-more="() => handleDeptPageLength(deptPageLength, true)"
          />
        </div>
        <template v-if="filters.team">
          <LeaderboardTable
            :rows="leaderboardRows"
            :loading="leaderboard.loading"
            :clickable="true"
            :title="`${filters.team} — ${__('Agents')}`"
            :total-count="leaderboardTotalCount"
            :page-length="leaderboardPageLength"
            @update:page-length="handleLeaderboardPageLength"
            @load-more="() => handleLeaderboardPageLength(leaderboardPageLength, true)"
            @select-agent="drillToAgent"
          />
        </template>
      </template>

    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";
import {
  Autocomplete, AxisChart, DateRangePicker, DonutChart,
  Dropdown, ListFooter, TabButtons, createResource, dayjs, usePageMeta, Tooltip,
} from "frappe-ui";
import { useScreenSize } from "@/composables/screen";
import { useStorage } from "@vueuse/core";
import { computed, defineComponent, h, onMounted, reactive, ref, watch } from "vue";
import { __ } from "@/translation";
import { useRouter } from "vue-router";
import LucideBuilding2   from "~icons/lucide/building-2";
import LucideCalendar    from "~icons/lucide/calendar";
import LucideChevronDown from "~icons/lucide/chevron-down";
import LucideChevronLeft from "~icons/lucide/chevron-left";
import LucideChevronRight from "~icons/lucide/chevron-right";
import LucideUser        from "~icons/lucide/user";
import LucideUsers       from "~icons/lucide/users";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideCheckCircle from "~icons/lucide/check-circle-2";
import LucideInbox       from "~icons/lucide/inbox";
import LucideUserX       from "~icons/lucide/user-x";
import LucideShieldAlert from "~icons/lucide/shield-alert";
import LucideZap         from "~icons/lucide/zap";
import LucideShieldCheck from "~icons/lucide/shield-check";
import LucideClock       from "~icons/lucide/clock";
import LucideTimer       from "~icons/lucide/timer";
import LucideStar        from "~icons/lucide/star";
import LucideBarChart2   from "~icons/lucide/bar-chart-2";
import SkeletonLoader from "@/components/SkeletonLoader.vue";

const { isMobileView } = useScreenSize();
const { isManager, userId } = useAuthStore();
const router = useRouter();

const COLORS = ["#318AD8","#48BB74","#F683AE","#FACF7A","#F56B6B","#44427B","#5FD8C4","#F8814F","#15CCEF","#A6B1B9"];
const DEFAULT_PAGE_LENGTH = 20;
const PAGE_LENGTH_OPTIONS = [20, 50, 100];

const AVATAR_COLORS = [
  ["#EFF6FF","#1D4ED8"], ["#F5F3FF","#6D28D9"], ["#ECFDF5","#047857"],
  ["#FFF7ED","#C2410C"], ["#FDF2F8","#9D174D"], ["#F0FDFA","#0F766E"],
  ["#EEF2FF","#4338CA"], ["#FEF2F2","#B91C1C"],
];

function getInitials(name: string): string {
  if (!name) return "?";
  const p = name.trim().split(/\s+/);
  return p.length === 1 ? p[0][0].toUpperCase() : (p[0][0] + p[p.length - 1][0]).toUpperCase();
}
function avatarStyle(idx: number): string {
  const [bg, color] = AVATAR_COLORS[idx % AVATAR_COLORS.length];
  return `background:${bg};color:${color};`;
}

// ── Date helpers ──────────────────────────────────────────────────────────────
function getLastXDays(range = 30): string {
  const today = new Date();
  const from = new Date(today);
  from.setDate(today.getDate() - range);
  return `${dayjs(from).format("YYYY-MM-DD")},${dayjs(today).format("YYYY-MM-DD")}`;
}
function formatDate(d: string) {
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric",
    year: new Date(d).getFullYear() !== new Date().getFullYear() ? "numeric" : undefined });
}
function formatPreset(range: string) {
  if (!range) return __("Last 30 Days");
  const [f, t] = range.split(",");
  return `${formatDate(f)} – ${formatDate(t)}`;
}

// ── Filters ───────────────────────────────────────────────────────────────────
const filters = reactive({ period: getLastXDays(30), team: null as string | null });
const preset = ref(__("Last 30 Days"));
const showDatePicker = ref(false);
const datePickerRef = ref(null);

const periodRange = computed({
  get: () => (filters.period ? filters.period.split(",") : []),
  set: (r: string[]) => {
    showDatePicker.value = false;
    filters.period = r?.length ? r.join(",") : getLastXDays(30);
    preset.value = formatPreset(filters.period);
  },
});

function parsedDates() {
  return { from_date: filters.period?.split(",")[0] ?? null, to_date: filters.period?.split(",")[1] ?? null };
}

const dateOptions = computed(() => [
  { group: __("Presets"), hideLabel: true, items: [
    { label: __("Today"),        onClick: () => { preset.value = __("Today");        filters.period = getLastXDays(0); } },
    { label: __("Last 7 Days"),  onClick: () => { preset.value = __("Last 7 Days");  filters.period = getLastXDays(7); } },
    { label: __("Last 30 Days"), onClick: () => { preset.value = __("Last 30 Days"); filters.period = getLastXDays(30); } },
    { label: __("Last 60 Days"), onClick: () => { preset.value = __("Last 60 Days"); filters.period = getLastXDays(60); } },
    { label: __("Last 90 Days"), onClick: () => { preset.value = __("Last 90 Days"); filters.period = getLastXDays(90); } },
  ]},
  { label: __("Custom Range"), onClick: () => {
    showDatePicker.value = true;
    setTimeout(() => datePickerRef.value?.open(), 0);
    preset.value = __("Custom Range");
    filters.period = null;
  }},
]);

// ── Manager tab + selection state ─────────────────────────────────────────────
const activeTab = useStorage("mcx_dashboard_tab", "overview");
const selectedAgent = ref<string | null>(null);

const teamList = createResource({
  url: "mcx_helpdesk.api.dashboard.get_team_list",
  cache: ["Mcx", "TeamList"],
  auto: isManager,
});

const selectedTeamOption = computed({
  get: () => {
    if (!filters.team) return null;
    const list = (teamList.data as any[]) || [];
    return list.find((o) => o.value === filters.team) ?? { value: filters.team, label: filters.team };
  },
  set: (opt: { value: string; label: string } | null) => {
    filters.team = opt?.value ?? null;
    selectedAgent.value = null;
  },
});

const agentList = createResource({
  url: "mcx_helpdesk.api.dashboard.get_agent_list",
  cache: ["Mcx", "AgentList"],
  makeParams: () => ({ team: filters.team || null }),
  auto: isManager,
});

const agentListPlaceholder = computed(() =>
  filters.team ? `${__("Agent in")} ${filters.team}` : __("Select Agent")
);

const selectedAgentOption = computed({
  get: () => {
    if (!selectedAgent.value) return null;
    const list = (agentList.data as any[]) || [];
    return list.find((o) => o.value === selectedAgent.value) ?? { value: selectedAgent.value, label: selectedAgent.value };
  },
  set: (opt: { value: string; label: string } | null) => { selectedAgent.value = opt?.value ?? null; },
});

const selectedAgentName = computed(() => {
  if (!selectedAgent.value) return "";
  const list = (agentList.data as any[]) || [];
  return list.find((o) => o.value === selectedAgent.value)?.label || selectedAgent.value;
});

// ── Tabs ──────────────────────────────────────────────────────────────────────
const tabButtons = computed(() => {
  if (isMobileView.value) return [
    { value: "overview", icon: h(LucideBuilding2, { class: "size-4" }) },
    { value: "agent",    icon: h(LucideUser,      { class: "size-4" }) },
    { value: "dept",     icon: h(LucideUsers,     { class: "size-4" }) },
  ];
  return [
    { value: "overview", iconLeft: h(LucideBuilding2, { class: "size-4" }), label: __("Overview") },
    { value: "agent",    iconLeft: h(LucideUser,      { class: "size-4" }), label: __("By Agent") },
    { value: "dept",     iconLeft: h(LucideUsers,     { class: "size-4" }), label: __("By Department") },
  ];
});

const pageTitle = computed(() => {
  if (!isManager) return "My Dashboard";
  if (activeTab.value === "overview") return filters.team ? `${filters.team} — Overview` : "Organization Overview";
  if (activeTab.value === "agent") {
    if (selectedAgent.value) return selectedAgentName.value || selectedAgent.value;
    return filters.team ? `${filters.team} — Agents` : "Agent Performance";
  }
  if (activeTab.value === "dept") return filters.team ? `${filters.team} — Department` : "Department Summary";
  return "Dashboard";
});

const agentActionTypes = [
  { value: "upcoming_sla", label: __("SLA Alerts") },
  { value: "pending",      label: __("Awaiting Response") },
  { value: "my_open",      label: __("My Open") },
  { value: "new_tickets",  label: __("Recently Assigned") },
];
const agentDrilldownActionTypes = [
  { value: "upcoming_sla", label: __("SLA Alerts") },
  { value: "pending",      label: __("Awaiting Response") },
  { value: "my_open",      label: __("Open") },
];
const managerActionTypes = [
  { value: "unassigned", label: __("Unassigned") },
  { value: "breached",   label: __("SLA Breached") },
  { value: "escalated",  label: __("Escalated") },
];

const agentActionTab = ref("upcoming_sla");
const managerActionTab = ref("unassigned");

const periodLabel = computed(() => preset.value || __("Selected period"));
const managerPeriodCards = computed(() => (numberCards.data as any[]) || []);

function masterChartSpanClass(chart: any) {
  if (chart?.type === "axis" && (chart?.data?.length ?? 0) > 4) {
    return "md:col-span-2";
  }
  return "";
}

// ── Chart helpers ─────────────────────────────────────────────────────────────
function isChartEmpty(chart: any) {
  if (!chart?.data?.length) return true;
  if (chart.type === "pie") {
    const col = chart.valueColumn || "count";
    return chart.data.filter((r: any) => Number(r[col]) > 0).length <= 1;
  }
  return chart.data.every((row: any) =>
    Object.entries(row).filter(([k]) => k !== "date").every(([, v]) => v === null || v === 0)
  );
}
function makeChart(chart: any) {
  const { title: _title, subtitle: _subtitle, ...rest } = chart;
  const cfg = { ...rest, colors: COLORS };
  if (cfg.type === "axis") return h(AxisChart, { config: cfg });
  if (cfg.type === "pie")  return h(DonutChart, { config: cfg });
  return null;
}

// ── API Resources ─────────────────────────────────────────────────────────────
const orgFilters = computed(() => ({ ...parsedDates(), team: filters.team }));

const numberCards = createResource({
  url: "helpdesk.api.dashboard.get_dashboard_data",
  cache: ["Mcx", "NumberCards"],
  makeParams: () => ({ dashboard_type: "number_card", filters: orgFilters.value }),
});
const trendData = createResource({
  url: "helpdesk.api.dashboard.get_dashboard_data",
  cache: ["Mcx", "TrendData"],
  makeParams: () => ({ dashboard_type: "trend", filters: orgFilters.value }),
});
const masterData = createResource({
  url: "helpdesk.api.dashboard.get_dashboard_data",
  cache: ["Mcx", "MasterData"],
  makeParams: () => ({ dashboard_type: "master", filters: orgFilters.value }),
});
const leaderboardPageLength = ref(DEFAULT_PAGE_LENGTH);
const deptPageLength = ref(DEFAULT_PAGE_LENGTH);

const leaderboard = createResource({
  url: "mcx_helpdesk.api.dashboard.get_agent_leaderboard",
  cache: ["Mcx", "Leaderboard"],
  makeParams: () => ({
    filters: { ...parsedDates(), team: filters.team },
    limit: leaderboardPageLength.value,
  }),
});

const leaderboardRows = computed(() => (leaderboard.data as any)?.rows || []);
const leaderboardTotalCount = computed(() => (leaderboard.data as any)?.total_count ?? 0);

function handleLeaderboardPageLength(count: number, loadMore = false) {
  if (loadMore) leaderboardPageLength.value += count;
  else leaderboardPageLength.value = count;
  leaderboard.reload();
}

function resetLeaderboardPagination() {
  leaderboardPageLength.value = DEFAULT_PAGE_LENGTH;
}

const agentTargetEmail = computed(() => isManager ? selectedAgent.value : userId);
const agentStats = createResource({
  url: "mcx_helpdesk.api.dashboard.get_agent_stats",
  makeParams: () => ({
    agent_email: agentTargetEmail.value,
    filters: { ...parsedDates(), team: filters.team },
  }),
});

const deptStats = createResource({
  url: "mcx_helpdesk.api.dashboard.get_department_stats",
  cache: ["Mcx", "DeptStats"],
  makeParams: () => ({ filters: orgFilters.value, limit: deptPageLength.value }),
});

const deptRows = computed(() => (deptStats.data as any)?.rows || []);
const deptTotalCount = computed(() => (deptStats.data as any)?.total_count ?? 0);

function handleDeptPageLength(count: number, loadMore = false) {
  if (loadMore) deptPageLength.value += count;
  else deptPageLength.value = count;
  deptStats.reload();
}

function resetDeptPagination() {
  deptPageLength.value = DEFAULT_PAGE_LENGTH;
}

const deptBarChart = computed(() => {
  const rows = (deptStats.data as any)?.chart_rows || (deptStats.data as any)?.rows;
  if (!rows?.length) return null;
  return {
    type: "axis",
    title: __("Tickets by Department"),
    subtitle: __("Ticket volume and SLA compliance per department"),
    xAxis: { key: "dept", type: "category", title: "Department" },
    yAxis: { title: "Tickets" },
    y2Axis: { title: "SLA %", yMin: 0, yMax: 100 },
    data: rows.map(r => ({ dept: r.dept, Tickets: r.total, "SLA %": r.sla_rate_pct })),
    series: [
      { name: "Tickets", type: "bar" },
      { name: "SLA %", type: "line", axis: "y2", showDataPoints: true },
    ],
  };
});

const visibleTrendCharts = computed(() =>
  ((trendData.data as any[]) || []).filter((chart) => !isChartEmpty(chart))
);
const visibleMasterCharts = computed(() =>
  ((masterData.data as any[]) || []).filter((chart) => !isChartEmpty(chart))
);

// ── Drill-down ────────────────────────────────────────────────────────────────
function drillToAgent(email: string) {
  selectedAgent.value = email;
  activeTab.value = "agent";
  agentStats.reload();
}

// ── Watchers ──────────────────────────────────────────────────────────────────
function reloadOrg() {
  resetLeaderboardPagination();
  numberCards.reload();
  trendData.reload();
  masterData.reload();
  leaderboard.reload();
}
function reloadAgent() { if (agentTargetEmail.value) agentStats.reload(); }

watch(() => filters.period, () => {
  if (showDatePicker.value && !filters.period) return;
  if (!isManager || activeTab.value === "overview") reloadOrg();
  if (!isManager || activeTab.value === "agent")   reloadAgent();
  if (isManager && activeTab.value === "dept") {
    resetDeptPagination();
    deptStats.reload();
  }
});

watch(() => filters.team, () => {
  if (!isManager) return;
  agentList.reload();
  resetLeaderboardPagination();
  if (activeTab.value === "overview") reloadOrg();
  else if (activeTab.value === "dept")  { resetDeptPagination(); deptStats.reload(); leaderboard.reload(); }
  else if (activeTab.value === "agent") { leaderboard.reload(); if (selectedAgent.value) reloadAgent(); }
});

watch(activeTab, (tab) => {
  if (tab === "overview") reloadOrg();
  else if (tab === "agent") {
    numberCards.reload();
    resetLeaderboardPagination();
    leaderboard.reload();
    if (selectedAgent.value) reloadAgent();
  }
  else if (tab === "dept")  { resetDeptPagination(); deptStats.reload(); resetLeaderboardPagination(); leaderboard.reload(); }
});

watch(selectedAgent, (v) => { if (v) reloadAgent(); });

onMounted(() => {
  if (!isManager) { agentStats.reload(); return; }
  reloadOrg();
  if (activeTab.value === "dept")  { deptStats.reload(); leaderboard.reload(); }
  if (activeTab.value === "agent") leaderboard.reload();
});

usePageMeta(() => ({ title: __("Dashboard") }));

// ══════════════════════════════════════════════════════════════════════════════
// Sub-components
// ══════════════════════════════════════════════════════════════════════════════

const KpiGroupLabel = defineComponent({
  name: "KpiGroupLabel",
  props: { label: { type: String, required: true } },
  setup(props) {
    return () => h("p", { class: "text-xs font-semibold uppercase tracking-wide text-ink-gray-5 mb-2" }, props.label);
  },
});

// ── ChartCard ─────────────────────────────────────────────────────────────────
const ChartCard = defineComponent({
  name: "ChartCard",
  props: { chart: { type: Object as () => any, required: true } },
  setup(props, { attrs }) {
    return () => {
      const c = props.chart;
      return h("div", {
        class: ["bg-surface-white rounded-xl border border-outline-gray-1 overflow-hidden shadow-sm", attrs.class],
      }, [
        h("div", { class: "px-5 pt-4 pb-2 border-b border-outline-gray-1 flex items-start gap-3" }, [
          h("div", { class: "size-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0 mt-0.5" },
            h(LucideBarChart2, { class: "size-4 text-blue-600" })
          ),
          h("div", [
            h("div", { class: "text-sm font-semibold text-ink-gray-8" }, c.title || ""),
            c.subtitle ? h("div", { class: "text-xs text-ink-gray-5 mt-0.5" }, c.subtitle) : null,
          ]),
        ]),
        h("div", { class: ["p-3", c.type === "pie" ? "min-h-80" : "min-h-72"] }, [makeChart(c)]),
      ]);
    };
  },
});

// ── ChartEmpty ────────────────────────────────────────────────────────────────
const ChartEmpty = defineComponent({
  name: "ChartEmpty",
  props: { title: String },
  setup(props) {
    return () => h("div", { class: "bg-surface-white rounded-xl border border-outline-gray-1 min-h-80 flex flex-col items-center justify-center gap-3 text-ink-gray-4" }, [
      h("div", { class: "size-12 rounded-full bg-surface-gray-2 flex items-center justify-center" },
        h(LucideCheckCircle, { class: "size-6 opacity-30" })
      ),
      h("p", { class: "text-sm" }, props.title ? `No ${props.title.toLowerCase()} data yet.` : "No data available."),
    ]);
  },
});

// ── KpiStrip ──────────────────────────────────────────────────────────────────
const KPI_ICON_MAP: Record<string, any> = {
  "Open":         LucideInbox,
  "Open Tickets": LucideInbox,
  "New Tickets":  LucideInbox,
  "Unassigned":   LucideUserX,
  "SLA Breached": LucideShieldAlert,
  "Escalated":    LucideZap,
  "No Response":  LucideClock,
  "SLA At Risk":  LucideShieldAlert,
  "Created in Period": LucideInbox,
  "% SLA Fulfilled": LucideShieldCheck,
  "SLA Rate":     LucideShieldCheck,
  "Avg. First Response": LucideClock,
  "First Response": LucideClock,
  "Avg. Resolution": LucideTimer,
  "Resolution":   LucideTimer,
  "Resolved":     LucideCheckCircle,
  "Avg. Feedback Rating": LucideStar,
  "Feedback":     LucideStar,
};

const KpiStrip = defineComponent({
  name: "KpiStrip",
  props: {
    cards:     { type: Array as () => any[], default: () => [] },
    clickable: { type: Boolean, default: false },
    compact:   { type: Boolean, default: false },
  },
  emits: ["card-click"],
  setup(props, { emit }) {
    const renderCard = (c: any) => {
      const Icon = KPI_ICON_MAP[c.title] || LucideInbox;
      const accentStyle = (a: string) => ({
        red:   { wrapper: "background:#FEF2F2;border-color:#FECACA;", icon: "background:#FEE2E2;color:#DC2626;", val: "color:#B91C1C;" },
        amber: { wrapper: "background:#FFFBEB;border-color:#FDE68A;", icon: "background:#FEF3C7;color:#D97706;", val: "color:#92400E;" },
        green: { wrapper: "background:#F0FDF4;border-color:#BBF7D0;", icon: "background:#DCFCE7;color:#16A34A;", val: "color:#15803D;" },
        default: { wrapper: "", icon: "background:#F3F4F6;color:#6B7280;", val: "" },
      })[a || "default"] || { wrapper: "", icon: "background:#F3F4F6;color:#6B7280;", val: "" };
      const s = accentStyle(c.accent);
      const canClick = props.clickable && c.action_tab;
      return h(Tooltip, { key: c.title, text: c.tooltip || c.title }, () =>
        h("div", {
          class: [
            "flex-1 min-w-0 rounded-xl border flex flex-col gap-2 transition-shadow",
            props.compact ? "p-3" : "p-4",
            canClick ? "cursor-pointer hover:shadow-md" : "cursor-default",
          ],
          style: s.wrapper || "background:white;border-color:#E5E7EB;",
          onClick: canClick ? () => emit("card-click", c) : undefined,
        }, [
          h("div", { class: "flex items-center justify-between" }, [
            h("div", { class: "size-8 rounded-lg flex items-center justify-center", style: s.icon },
              h(Icon, { style: "width:16px;height:16px;" })
            ),
          ]),
          h("div", [
            h("div", { class: "text-2xl font-bold leading-none", style: s.val || "color:#111827;" }, [
              String(c.value),
              c.suffix ? h("span", { class: "text-sm font-normal ml-0.5", style: "color:#9CA3AF;" }, c.suffix) : null,
            ]),
            h("div", { class: "text-xs mt-1 truncate", style: "color:#6B7280;", title: c.title }, c.title),
          ]),
        ])
      );
    };

    return () => h("div", { class: "flex w-full gap-2 min-w-0" }, props.cards.map(renderCard));
  },
});

// ── SlaBar ────────────────────────────────────────────────────────────────────
function slaBar(pct: number) {
  const color = pct >= 80 ? "#22C55E" : pct >= 60 ? "#F59E0B" : "#EF4444";
  const textColor = pct >= 80 ? "#15803D" : pct >= 60 ? "#92400E" : "#B91C1C";
  return h("div", { class: "flex items-center gap-2" }, [
    h("div", { class: "flex-1 rounded-full overflow-hidden", style: "height:5px;background:#E5E7EB;min-width:40px;" }, [
      h("div", { style: `height:100%;border-radius:999px;background:${color};width:${Math.min(100, pct)}%;transition:width .4s ease;` }),
    ]),
    h("span", { class: "text-xs font-semibold tabular-nums", style: `color:${textColor};min-width:36px;text-align:right;` }, `${pct}%`),
  ]);
}

// ── List pagination footer (Frappe ListFooter pattern) ───────────────────────
function renderListFooter(
  rowCount: number,
  totalCount: number,
  pageLength: number,
  onUpdatePageLength: (count: number) => void,
  onLoadMore: () => void,
) {
  if (!rowCount) return null;
  return h("div", { class: "px-4 py-2 border-t border-outline-gray-1" }, [
    h(ListFooter, {
      modelValue: pageLength,
      "onUpdate:modelValue": onUpdatePageLength,
      options: {
        rowCount,
        totalCount,
        pageLengthOptions: PAGE_LENGTH_OPTIONS,
      },
      onLoadMore,
    }),
  ]);
}

// ── ActionTicketsPanel ────────────────────────────────────────────────────────
const PRIORITY_STYLE: Record<string, string> = {
  Urgent: "background:#FEF2F2;color:#DC2626;border-color:#FECACA;",
  High:   "background:#FFF7ED;color:#EA580C;border-color:#FED7AA;",
  Medium: "background:#FFFBEB;color:#D97706;border-color:#FDE68A;",
  Low:    "background:#F0FDF4;color:#16A34A;border-color:#BBF7D0;",
};
const PRIORITY_DOT: Record<string, string> = {
  Urgent: "#DC2626", High: "#EA580C", Medium: "#F59E0B", Low: "#22C55E",
};

const ActionTicketsPanel = defineComponent({
  name: "ActionTicketsPanel",
  props: {
    listTypes:  { type: Array as () => { value: string; label: string }[], required: true },
    team:       { type: String as () => string | null, default: null },
    agentEmail: { type: String as () => string | null, default: null },
    activeList: { type: String, default: "" },
  },
  emits: ["update:activeList"],
  setup(props, { emit }) {
    const activeList = computed({
      get: () => props.activeList || props.listTypes[0]?.value || "upcoming_sla",
      set: (v: string) => emit("update:activeList", v),
    });

    const pageLength = ref(DEFAULT_PAGE_LENGTH);

    const tickets$ = createResource({
      url: "mcx_helpdesk.api.dashboard.get_action_tickets",
      makeParams: () => ({
        list_type: activeList.value,
        filters: props.team ? { team: props.team } : {},
        agent_email: props.agentEmail || undefined,
        limit: pageLength.value,
      }),
    });

    function handlePageLength(count: number, loadMore = false) {
      if (loadMore) pageLength.value += count;
      else pageLength.value = count;
      tickets$.reload();
    }

    watch(
      () => [activeList.value, props.team, props.agentEmail],
      () => {
        pageLength.value = DEFAULT_PAGE_LENGTH;
        tickets$.reload();
      },
      { immediate: true },
    );

    function goToTicket(t: any) { router.push({ name: "TicketAgent", params: { ticketId: String(t.name) } }); }

    return () => {
      const tickets = tickets$.data?.tickets || [];
      const total = tickets$.data?.total_count ?? tickets$.data?.total_pending_tickets ?? 0;

      return h("div", { class: "bg-surface-white rounded-xl border border-outline-gray-1 overflow-hidden shadow-sm" }, [
        // Header
        h("div", { class: "flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-outline-gray-1" }, [
          h("div", { class: "flex items-center gap-2.5" }, [
            h("div", { class: "size-7 rounded-lg flex items-center justify-center", style: "background:#FEF3C7;" },
              h(LucideAlertTriangle, { style: "width:14px;height:14px;color:#D97706;" })
            ),
            h("span", { class: "text-sm font-semibold text-ink-gray-8" }, __("Needs Attention")),
            total > 0
              ? h("span", {
                  class: "text-xs font-bold rounded-full px-2 py-0.5",
                  style: "background:#FEF3C7;color:#92400E;",
                }, String(total))
              : null,
          ]),
          h(TabButtons, {
            modelValue: activeList.value,
            "onUpdate:modelValue": (v: string) => { activeList.value = v; },
            buttons: props.listTypes.map(t => ({ label: t.label, value: t.value })),
          }),
        ]),

        // Body
        tickets$.loading
          ? h("div", { class: "px-4 py-4" }, [h(SkeletonLoader, { variants: ["bar-chart"], barChartCount: 1, loading: true })])
          : tickets.length === 0
          ? h("div", { class: "px-4 py-8 flex flex-col items-center gap-2 text-ink-gray-4" }, [
              h("div", { class: "size-10 rounded-full flex items-center justify-center", style: "background:#F0FDF4;" },
                h(LucideCheckCircle, { style: "width:20px;height:20px;color:#22C55E;" })
              ),
              h("span", { class: "text-sm font-medium", style: "color:#6B7280;" }, __("All clear — no tickets in this list")),
            ])
          : h("div", { class: "overflow-x-auto" }, [
              h("table", { class: "w-full text-sm" }, [
                h("thead", [
                  h("tr", { class: "border-b border-outline-gray-1 text-xs uppercase tracking-wide", style: "color:#9CA3AF;background:#F9FAFB;" }, [
                    h("th", { class: "text-left px-4 py-2.5 font-medium" }, __("ID")),
                    h("th", { class: "text-left px-4 py-2.5 font-medium" }, __("Subject")),
                    h("th", { class: "text-left px-4 py-2.5 font-medium" }, __("Priority")),
                    h("th", { class: "text-left px-4 py-2.5 font-medium" }, __("Department")),
                    h("th", { class: "text-left px-4 py-2.5 font-medium" }, __("Status")),
                  ]),
                ]),
                h("tbody", tickets.map((t: any, i: number) => {
                  const dotColor = PRIORITY_DOT[t.priority] || "#9CA3AF";
                  return h("tr", {
                    key: t.name,
                    class: "border-b border-outline-gray-1 last:border-0 cursor-pointer transition-colors group",
                    style: i % 2 === 1 ? "background:#FAFAFA;" : "",
                    onMouseenter: (e: Event) => { (e.currentTarget as HTMLElement).style.background = "#EFF6FF"; },
                    onMouseleave: (e: Event) => { (e.currentTarget as HTMLElement).style.background = i % 2 === 1 ? "#FAFAFA" : ""; },
                    onClick: () => goToTicket(t),
                  }, [
                    h("td", { class: "px-4 py-2.5 whitespace-nowrap", style: "font-family:monospace;font-size:11px;color:#6B7280;" }, t.name),
                    h("td", { class: "px-4 py-2.5 max-w-xs" }, [
                      h("div", { class: "flex items-center gap-2" }, [
                        h("div", { class: "shrink-0 rounded-full size-1.5", style: `background:${dotColor};` }),
                        h("span", { class: "truncate font-medium text-ink-gray-8 group-hover:text-blue-600 transition-colors text-sm" }, t.subject),
                      ]),
                    ]),
                    h("td", { class: "px-4 py-2.5 whitespace-nowrap" }, [
                      t.priority
                        ? h("span", {
                            class: "text-xs font-semibold px-2 py-0.5 rounded-full border",
                            style: PRIORITY_STYLE[t.priority] || "background:#F3F4F6;color:#374151;border-color:#E5E7EB;",
                          }, t.priority)
                        : h("span", { style: "color:#D1D5DB;" }, "—"),
                    ]),
                    h("td", { class: "px-4 py-2.5 whitespace-nowrap text-xs", style: "color:#6B7280;" }, t.agent_group || __("Unassigned")),
                    h("td", { class: "px-4 py-2.5 whitespace-nowrap" }, [
                      t.status
                        ? h("span", { class: "text-xs px-2 py-0.5 rounded-full", style: "background:#F3F4F6;color:#374151;" }, t.status)
                        : h("span", { style: "color:#D1D5DB;" }, "—"),
                    ]),
                  ]);
                })),
              ]),
            ]),
        renderListFooter(
          tickets.length,
          total,
          pageLength.value,
          (count) => handlePageLength(count),
          () => handlePageLength(pageLength.value, true),
        ),
      ]);
    };
  },
});

// ── AgentPeriodKpis ───────────────────────────────────────────────────────────
const AgentPeriodKpis = defineComponent({
  name: "AgentPeriodKpis",
  props: {
    stats:   { type: Object as () => Record<string, any> | null, default: null },
    loading: { type: Boolean, default: false },
  },
  setup(props) {
    const periodCards = computed(() => {
      if (!props.stats) return [];
      const s = props.stats;
      const f = (v: any, sfx: string) => v == null ? { value: "—", suffix: "" } : { value: v, suffix: sfx };
      const cards = [
        { title: __("Resolved"),       ...f(s.resolved_tickets, ""),       tooltip: __("Tickets resolved in selected period"), accent: "green" },
        { title: __("SLA Rate"),       ...f(s.sla_rate_pct, "%"),          tooltip: __("% of SLA-tracked tickets fulfilled"), accent: (s.sla_rate_pct ?? 0) >= 80 ? "green" : "red" },
        { title: __("First Response"), ...f(s.avg_first_response_hrs, " hrs"), tooltip: __("Average first response time"), accent: "default" },
        { title: __("Resolution"),     ...f(s.avg_resolution_days, " days"),   tooltip: __("Average resolution time"), accent: "default" },
      ];
      if (s.avg_feedback != null) {
        cards.push({ title: __("Feedback"), ...f(s.avg_feedback, "/5"), tooltip: __("Average CSAT score"), accent: (s.avg_feedback ?? 0) >= 4 ? "green" : "default" });
      }
      return cards;
    });

    return () => {
      if (props.loading) {
        return h("div", { class: "flex w-full gap-3" },
          Array(4).fill(0).map((_, i) =>
            h("div", { key: i, class: "flex-1 h-20 rounded-xl bg-surface-white animate-pulse border border-outline-gray-1" })
          )
        );
      }
      const banners: any[] = [];
      const escalated = props.stats?.escalated_open ?? 0;
      if (escalated > 0) {
        banners.push(
          h("div", { class: "mb-3 flex items-center gap-3 rounded-xl px-4 py-3 border", style: "background:#FFFBEB;border-color:#FDE68A;" }, [
            h(LucideAlertTriangle, { style: "width:16px;height:16px;color:#D97706;flex-shrink:0;" }),
            h("span", { class: "text-sm font-medium", style: "color:#92400E;" },
              `${escalated} open ${escalated === 1 ? "ticket is" : "tickets are"} escalated.`),
          ])
        );
      }
      return h("div", [...banners, h(KpiStrip, { cards: periodCards.value })]);
    };
  },
});

// ── AgentAnalyticsSection ─────────────────────────────────────────────────────
const AgentAnalyticsSection = defineComponent({
  name: "AgentAnalyticsSection",
  props: {
    stats:   { type: Object as () => Record<string, any> | null, default: null },
    loading: { type: Boolean, default: false },
  },
  setup(props) {
    const trendCfg = computed(() => {
      const rows = props.stats?.ticket_trend;
      if (!rows?.length) return null;
      return {
        type: "axis", title: __("Ticket Trend"), subtitle: __("Daily open vs resolved with SLA compliance"),
        xAxis: { key: "date", type: "time", title: "Date", timeGrain: "day" },
        yAxis: { title: "Tickets" }, y2Axis: { title: "SLA %", yMin: 0, yMax: 100 },
        data: rows,
        series: [{ name: "Resolved", type: "bar" }, { name: "Open", type: "bar" }, { name: "SLA %", type: "line", axis: "y2", showDataPoints: true }],
        stacked: true,
      };
    });

    const byTypeCfg = computed(() => {
      const rows = props.stats?.by_type;
      if (!rows || rows.length < 2) return null;
      return { type: "pie", title: __("By Issue Type"), subtitle: __("Share of your tickets by issue type"), data: rows, categoryColumn: "type", valueColumn: "count" };
    });

    const byPriorityCfg = computed(() => {
      const rows = props.stats?.by_priority;
      if (!rows || rows.length < 2) return null;
      return { type: "pie", title: __("By Priority"), subtitle: __("Share of your tickets by priority"), data: rows, categoryColumn: "priority", valueColumn: "count" };
    });

    return () => {
      if (props.loading) {
        return h(SkeletonLoader, { variants: ["bar-chart"], barChartCount: 2, loading: true });
      }
      if (!props.stats) {
        return h("div", { class: "bg-surface-white rounded-xl border border-outline-gray-1 py-16 flex flex-col items-center gap-3 text-ink-gray-4" }, [
          h("p", { class: "text-sm" }, __("No data available for this period.")),
        ]);
      }

      const breakdown: any[] = [];
      if (byPriorityCfg.value) breakdown.push(h(ChartCard, { chart: byPriorityCfg.value }));
      if (byTypeCfg.value) breakdown.push(h(ChartCard, { chart: byTypeCfg.value }));

      return h("div", [
        trendCfg.value
          ? h(ChartCard, { chart: trendCfg.value, class: "mb-4" })
          : null,
        breakdown.length
          ? h("div", { class: "grid grid-cols-1 md:grid-cols-2 gap-4" }, breakdown)
          : null,
      ].filter(Boolean));
    };
  },
});

// ── LeaderboardTable ──────────────────────────────────────────────────────────
const LeaderboardTable = defineComponent({
  name: "LeaderboardTable",
  props: {
    rows:        { type: Array as () => any[], default: () => [] },
    loading:     { type: Boolean, default: false },
    clickable:   { type: Boolean, default: false },
    title:       { type: String, default: "" },
    totalCount:  { type: Number, default: 0 },
    pageLength:  { type: Number, default: DEFAULT_PAGE_LENGTH },
  },
  emits: ["select-agent", "update:pageLength", "loadMore"],
  setup(props, { emit }) {
    return () => {
      if (props.loading) {
        return h("div", { class: "bg-surface-white rounded-xl border border-outline-gray-1 overflow-hidden animate-pulse" }, [
          h("div", { class: "h-12 border-b", style: "background:#F9FAFB;" }),
          ...Array(4).fill(0).map((_, i) => h("div", { key: i, class: "h-14 border-b", style: "background:white;" })),
        ]);
      }

      const rows = props.rows || [];
      if (!rows.length) return h("div", { class: "bg-surface-white rounded-xl border border-outline-gray-1 px-4 py-12 text-center text-sm", style: "color:#9CA3AF;" },
        __("No agent data available for this period.")
      );

      const title = props.title || __("Agent Leaderboard");

      const RANK_STYLE = [
        { style: "background:#FEF3C7;color:#D97706;font-weight:700;", label: "1" },
        { style: "background:#F3F4F6;color:#6B7280;font-weight:700;", label: "2" },
        { style: "background:#FFF7ED;color:#EA580C;font-weight:600;", label: "3" },
      ];

      const rankEl = (i: number) => {
        const s = RANK_STYLE[i];
        if (s) return h("span", { class: "inline-flex size-6 items-center justify-center rounded-full text-xs", style: s.style }, s.label);
        return h("span", { class: "text-xs pl-1.5", style: "color:#9CA3AF;" }, `${i + 1}`);
      };

      return h("div", { class: "bg-surface-white rounded-xl border border-outline-gray-1 overflow-hidden shadow-sm" }, [
        // Panel header
        h("div", { class: "flex items-center justify-between px-5 py-3.5 border-b border-outline-gray-1", style: "background:#F9FAFB;" }, [
          h("div", { class: "flex items-center gap-2" }, [
            h("div", { class: "size-7 rounded-lg flex items-center justify-center", style: "background:#EFF6FF;" },
              h(LucideUsers, { style: "width:14px;height:14px;color:#2563EB;" })
            ),
            h("span", { class: "text-sm font-semibold text-ink-gray-8" }, title),
          ]),
          props.clickable ? h("span", { class: "text-xs", style: "color:#9CA3AF;" }, __("Click a row for details →")) : null,
        ]),
        // Table
        h("div", { class: "overflow-x-auto" }, [
          h("table", { class: "w-full text-sm" }, [
            h("thead", [
              h("tr", { class: "border-b border-outline-gray-1 text-xs uppercase tracking-wide", style: "color:#9CA3AF;background:#F9FAFB;" }, [
                h("th", { class: "px-4 py-2.5 text-left w-10" }, "#"),
                h("th", { class: "px-4 py-2.5 text-left" }, __("Agent")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Open")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Period")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Resolved")),
                h("th", { class: "px-5 py-2.5 text-right", style: "min-width:140px;" }, __("SLA Rate")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Breached")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Avg. Resol.")),
              ]),
            ]),
            h("tbody", rows.map((row, idx) =>
              h("tr", {
                key: row.agent_email,
                class: ["border-b border-outline-gray-1 last:border-0 transition-colors", props.clickable ? "cursor-pointer" : ""],
                style: idx % 2 === 1 ? "background:#FAFAFA;" : "background:white;",
                onMouseenter: props.clickable ? (e: Event) => { (e.currentTarget as HTMLElement).style.background = "#EFF6FF"; } : undefined,
                onMouseleave: props.clickable ? (e: Event) => { (e.currentTarget as HTMLElement).style.background = idx % 2 === 1 ? "#FAFAFA" : "white"; } : undefined,
                onClick: props.clickable ? () => emit("select-agent", row.agent_email) : undefined,
              }, [
                h("td", { class: "px-4 py-3.5" }, rankEl(idx)),
                h("td", { class: "px-4 py-3.5" }, [
                  h("div", { class: "flex items-center gap-3" }, [
                    h("div", {
                      class: "size-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0",
                      style: avatarStyle(idx),
                    }, getInitials(row.agent_name)),
                    h("div", [
                      h("div", { class: "font-semibold text-ink-gray-8 text-sm leading-tight" }, row.agent_name),
                      h("div", { class: "text-xs mt-0.5", style: "color:#9CA3AF;" }, row.agent_email),
                    ]),
                  ]),
                ]),
                h("td", { class: "px-4 py-3.5 text-right" }, [
                  (row.open ?? 0) > 0
                    ? h("span", { class: "text-xs font-bold px-2 py-0.5 rounded-full", style: "background:#FEF3C7;color:#92400E;" }, row.open)
                    : h("span", { style: "color:#D1D5DB;" }, "—"),
                ]),
                h("td", { class: "px-4 py-3.5 text-right text-sm", style: "color:#374151;" }, row.total),
                h("td", { class: "px-4 py-3.5 text-right text-sm font-medium", style: "color:#059669;" }, row.resolved),
                h("td", { class: "px-5 py-3.5" }, slaBar(row.sla_rate_pct ?? 0)),
                h("td", { class: "px-4 py-3.5 text-right" }, [
                  (row.breached_open ?? 0) > 0
                    ? h("span", { class: "text-xs font-bold px-2 py-0.5 rounded-full", style: "background:#FEF2F2;color:#DC2626;" }, row.breached_open)
                    : h("span", { style: "color:#D1D5DB;" }, "—"),
                ]),
                h("td", { class: "px-4 py-3.5 text-right flex items-center justify-end gap-1" }, [
                  h("span", { class: "text-sm", style: "color:#6B7280;" }, row.avg_resolution_days ? `${row.avg_resolution_days}d` : "—"),
                  props.clickable ? h(LucideChevronRight, { style: "width:14px;height:14px;color:#D1D5DB;display:inline;" }) : null,
                ]),
              ])
            )),
          ]),
        ]),
        renderListFooter(
          rows.length,
          props.totalCount || rows.length,
          props.pageLength,
          (count) => emit("update:pageLength", count),
          () => emit("loadMore"),
        ),
      ]);
    };
  },
});

// ── DeptTable ─────────────────────────────────────────────────────────────────
const DeptTable = defineComponent({
  name: "DeptTable",
  props: {
    rows:       { type: Array as () => any[], default: () => [] },
    loading:    { type: Boolean, default: false },
    totalCount: { type: Number, default: 0 },
    pageLength: { type: Number, default: DEFAULT_PAGE_LENGTH },
  },
  emits: ["update:pageLength", "loadMore"],
  setup(props, { emit }) {
    return () => {
      if (props.loading) {
        return h("div", { class: "bg-surface-white rounded-xl border border-outline-gray-1 animate-pulse overflow-hidden" }, [
          h("div", { class: "h-12 border-b", style: "background:#F9FAFB;" }),
          ...Array(4).fill(0).map((_, i) => h("div", { key: i, class: "h-12 border-b", style: "background:white;" })),
        ]);
      }

      const rows = props.rows || [];
      if (!rows.length) return h("div", { class: "bg-surface-white rounded-xl border border-outline-gray-1 px-4 py-12 text-center text-sm", style: "color:#9CA3AF;" },
        __("No department data available for this period.")
      );

      return h("div", { class: "bg-surface-white rounded-xl border border-outline-gray-1 overflow-hidden shadow-sm" }, [
        h("div", { class: "flex items-center gap-2 px-5 py-3.5 border-b border-outline-gray-1", style: "background:#F9FAFB;" }, [
          h("div", { class: "size-7 rounded-lg flex items-center justify-center", style: "background:#EFF6FF;" },
            h(LucideBuilding2, { style: "width:14px;height:14px;color:#2563EB;" })
          ),
          h("span", { class: "text-sm font-semibold text-ink-gray-8" }, __("Department Summary")),
        ]),
        h("div", { class: "overflow-x-auto" }, [
          h("table", { class: "w-full text-sm" }, [
            h("thead", [
              h("tr", { class: "border-b border-outline-gray-1 text-xs uppercase tracking-wide", style: "color:#9CA3AF;background:#F9FAFB;" }, [
                h("th", { class: "px-5 py-2.5 text-left"  }, __("Department")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Total")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Open")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Resolved")),
                h("th", { class: "px-5 py-2.5 text-right", style: "min-width:140px;" }, __("SLA Rate")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Avg. Resol.")),
                h("th", { class: "px-4 py-2.5 text-right" }, __("Escalated")),
              ]),
            ]),
            h("tbody", rows.map((row, idx) =>
              h("tr", {
                key: row.dept,
                class: "border-b border-outline-gray-1 last:border-0 transition-colors hover:bg-blue-50",
                style: idx % 2 === 1 ? "background:#FAFAFA;" : "background:white;",
              }, [
                h("td", { class: "px-5 py-3.5" }, [
                  h("div", { class: "flex items-center gap-2.5" }, [
                    h("div", { class: "size-7 rounded-lg flex items-center justify-center", style: `background:${AVATAR_COLORS[idx % AVATAR_COLORS.length][0]};` },
                      h("span", { class: "text-xs font-bold", style: `color:${AVATAR_COLORS[idx % AVATAR_COLORS.length][1]};` }, row.dept?.[0]?.toUpperCase() || "?")
                    ),
                    h("span", { class: "font-semibold text-ink-gray-8" }, row.dept),
                  ]),
                ]),
                h("td", { class: "px-4 py-3.5 text-right text-sm", style: "color:#374151;" }, row.total),
                h("td", { class: "px-4 py-3.5 text-right" }, [
                  row.open > 0
                    ? h("span", { class: "text-xs font-bold px-2 py-0.5 rounded-full", style: "background:#FEF3C7;color:#92400E;" }, row.open)
                    : h("span", { style: "color:#D1D5DB;" }, "—"),
                ]),
                h("td", { class: "px-4 py-3.5 text-right text-sm font-medium", style: "color:#059669;" }, row.resolved),
                h("td", { class: "px-5 py-3.5" }, slaBar(row.sla_rate_pct ?? 0)),
                h("td", { class: "px-4 py-3.5 text-right text-sm", style: "color:#6B7280;" }, row.avg_resolution_days ? `${row.avg_resolution_days}d` : "—"),
                h("td", { class: "px-4 py-3.5 text-right" }, [
                  row.escalated > 0
                    ? h("span", { class: "text-xs font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1", style: "background:#FFFBEB;color:#D97706;" }, [
                        h(LucideAlertTriangle, { style: "width:11px;height:11px;" }), String(row.escalated),
                      ])
                    : h("span", { style: "color:#D1D5DB;" }, "—"),
                ]),
              ])
            )),
          ]),
        ]),
        renderListFooter(
          rows.length,
          props.totalCount || rows.length,
          props.pageLength,
          (count) => emit("update:pageLength", count),
          () => emit("loadMore"),
        ),
      ]);
    };
  },
});
</script>

<style scoped>
:deep(.form-control button) {
  @apply text-sm rounded h-7 py-1.5 border border-outline-gray-2 bg-surface-white placeholder-ink-gray-4 hover:border-outline-gray-3 hover:shadow-sm focus:bg-surface-white focus:border-outline-gray-4 focus:shadow-sm focus:ring-0 focus-visible:ring-0 text-ink-gray-8 transition-colors w-full;
}
:deep(.form-control button > div) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:deep(.form-control div) { width: 100%; display: flex; }
</style>
