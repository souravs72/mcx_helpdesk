<template>
  <div class="flex h-full flex-col">
    <div class="shrink-0 px-4 pb-4 flex flex-col">
      <!-- User avatar with buttons -->
      <TicketContact />
      <!-- Core Fields -->
      <div class="mt-4">
        <div
          v-for="(section, index) in coreFields"
          :key="index"
          :class="
            section.group ? 'flex gap-2 items-start max-w-full mb-3' : 'mb-3'
          "
        >
          <template v-for="field in section.fields">
            <Link
              v-if="field.visible"
              :key="field.fieldname"
              :ref="(el) => setFieldRef(field.fieldname, el)"
              class="form-control-core"
              :id="field.fieldname"
              :class="section.group ? 'flex-1 min-w-0' : 'w-full'"
              :page-length="10"
              :label="__(field.label)"
              :placeholder="__(field.placeholder)"
              :doctype="field.doctype"
              :filters="field.filters"
              :modelValue="__(field.value)"
              :required="field.required"
              @update:model-value="
              (val:string) => handleFieldUpdate(field.fieldname, val,true)
            "
            />
          </template>
        </div>

        <!-- Assignee component -->
        <AssignTo />
      </div>

      <!-- MCX: Proactive SLA risk banner -->
      <div
        v-if="slaRiskBanner.visible"
        class="mt-3 rounded-lg border px-3 py-2.5"
        :class="slaRiskBanner.wrapClass"
      >
        <div class="flex items-center gap-2">
          <LucideClock class="size-3.5 shrink-0" :class="slaRiskBanner.iconClass" />
          <span class="text-sm font-semibold leading-tight" :class="slaRiskBanner.textClass">
            {{ slaRiskBanner.title }}
          </span>
          <Badge
            :label="slaRiskBanner.badge"
            :theme="slaRiskBanner.badgeTheme"
            variant="subtle"
            class="ml-auto shrink-0"
          />
        </div>
        <p class="mt-1 pl-5 text-xs leading-tight" :class="slaRiskBanner.textClass" style="opacity: 0.8">
          {{ slaRiskBanner.detail }}
        </p>
      </div>

      <!-- MCX: AI assist -->
      <AiAssistPanel class="mt-3" />

      <!-- MCX: Escalation status banner -->
      <div
        v-if="escalationBanner.visible"
        class="mt-3 rounded-lg border px-3 py-2.5"
        :class="escalationBanner.wrapClass"
      >
        <div class="flex items-center gap-2">
          <LucideAlertTriangle class="size-3.5 shrink-0" :class="escalationBanner.iconClass" />
          <span class="text-sm font-semibold leading-tight" :class="escalationBanner.textClass">
            {{ escalationBanner.title }}
          </span>
          <Badge
            :label="escalationBanner.badge"
            :theme="escalationBanner.badgeTheme"
            variant="subtle"
            class="ml-auto shrink-0"
          />
        </div>
        <p
          v-if="escalationBanner.since"
          class="mt-1 pl-5 text-xs leading-tight"
          :class="escalationBanner.textClass"
          style="opacity: 0.75"
        >
          Escalated {{ escalationBanner.since }}
        </p>
      </div>
    </div>

    <!-- Scrollable sections: Ticket Info + Recent / Similar Tickets -->
    <div
      class="border-t flex-1 min-h-0 overflow-y-auto divide-y-[1px]"
      v-if="Boolean(customFields.length) || showRecentSimilarTickets"
    >
      <!-- Ticket Info (custom fields) -->
      <div v-if="Boolean(customFields.length)">
        <Section label="Ticket Info" v-model:opened="openedSections.ticketInfo">
          <template #header="{ opened, toggle }">
            <div
              class="flex gap-2.5 items-center justify-between sticky top-0 bg-surface-white z-10 px-4 py-4 cursor-pointer"
              @click="toggle"
            >
              <span class="text-ink-gray-8 font-semibold text-base select-none">
                {{ __("Ticket Info") }}
              </span>
              <LucideChevronRight
                class="size-4 text-ink-gray-6"
                :class="{ 'rotate-90': opened }"
              />
            </div>
          </template>
          <div
            class="space-y-1.5 px-4 mb-2 mt-0.5"
            v-if="Boolean(customFields.length)"
          >
            <template v-for="field in customFields">
              <TicketField
                v-if="field.visible"
                :key="field.fieldname"
                :field="field"
                :value="field.value"
                @change="
                  ({ fieldname, value }) => handleFieldUpdate(fieldname, value)
                "
              />
            </template>
          </div>
        </Section>
      </div>

      <!-- Recent / Similar Tickets -->
      <template v-if="showRecentSimilarTickets">
        <div v-for="section in sections" :key="section.label">
          <Section
            :label="section.label"
            :hideLabel="section.hideLabel"
            v-model:opened="openedSections[section.key]"
          >
            <template #header="{ opened, toggle }">
              <div
                class="flex gap-2.5 items-center justify-between sticky top-0 bg-surface-white z-10 px-4 py-4 cursor-pointer"
                @click="toggle"
              >
                <Tooltip :text="section.tooltipMessage">
                  <span
                    class="text-ink-gray-8 font-semibold text-base select-none"
                  >
                    {{ __(section.label) }}
                  </span>
                </Tooltip>
                <LucideChevronRight
                  class="size-4 text-ink-gray-6"
                  :class="{ 'rotate-90': opened }"
                />
              </div>
            </template>
            <ul class="pt-0 px-5 divide-y divide-outline-gray-1 pb-4">
              <li
                v-for="t in section.tickets"
                :key="t.name"
                @click="openTicket(t.name)"
              >
                <div
                  class="-mx-2 px-2 py-3 cursor-pointer rounded hover:bg-surface-gray-2 transition-colors"
                >
                  <p class="text-sm font-base text-ink-gray-9 truncate mb-2">
                    {{ t.subject }}
                  </p>
                  <div class="flex items-center justify-between gap-2">
                    <p class="text-sm text-ink-gray-5 shrink-0">
                      {{ formatDate(t.creation as string) + " · " }}
                      <span class="">{{ "#" + t.name }}</span>
                    </p>
                    <span
                      class="text-xs px-2 py-0.5 font-base shrink-0 rounded-sm"
                      :class="getStatusColor(t.status as string)"
                    >
                      {{ t.status }}
                    </span>
                  </div>
                </div>
              </li>
            </ul>
          </Section>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Link } from "@/components";
import { parseField } from "@/composables/formCustomisation";
import { useNotifyTicketUpdate } from "@/composables/realtime";
import { useShortcut } from "@/composables/shortcuts";
import { getMeta } from "@/stores/meta";
import { useTicketStatusStore } from "@/stores/ticketStatus";
import {
  ActivitiesSymbol,
  AssigneeSymbol,
  CustomizationSymbol,
  FieldValue,
  RecentSimilarTicketsSymbol,
  TicketSymbol,
} from "@/types";
import { useStorage } from "@vueuse/core";
import { Badge, dayjs, Tooltip } from "frappe-ui";
import { computed, inject, ref } from "vue";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideChevronRight from "~icons/lucide/chevron-right";
import LucideClock from "~icons/lucide/clock";
import Section from "@/components/Section.vue";
import TicketField from "@/components/TicketField.vue";
import AssignTo from "@/components/ticket-agent/AssignTo.vue";
import AiAssistPanel from "@/components/ticket-agent/AiAssistPanel.vue";
import TicketContact from "@/components/ticket-agent/TicketContact.vue";

const ticket = inject(TicketSymbol)!;
const assignees = inject(AssigneeSymbol)!;
const customizations = inject(CustomizationSymbol)!;

const slaRiskBanner = computed(() => {
  const doc = ticket.value?.doc;
  if (!doc) return { visible: false };

  const risk = doc.mcx_sla_risk_level;
  if (!risk || risk === "None" || doc.agreement_status === "Failed") {
    return { visible: false };
  }

  const pct = doc.mcx_sla_risk_pct ? `${Math.round(doc.mcx_sla_risk_pct)}%` : "";
  const target = doc.mcx_sla_risk_target || "SLA";
  const detail = `${target} window ${pct} elapsed — act before SLA breach.`;

  if (risk === "Critical") {
    return {
      visible: true,
      title: "SLA breach imminent",
      badge: "Critical",
      badgeTheme: "red",
      wrapClass: "border-red-200 bg-red-50",
      iconClass: "text-red-500",
      textClass: "text-red-700",
      detail,
    };
  }

  return {
    visible: true,
    title: "SLA deadline approaching",
    badge: "Warning",
    badgeTheme: "orange",
    wrapClass: "border-amber-200 bg-amber-50",
    iconClass: "text-amber-500",
    textClass: "text-amber-800",
    detail,
  };
});

const escalationBanner = computed(() => {
  const doc = ticket.value?.doc;
  if (!doc) return { visible: false };

  const level: number = doc.mcx_escalation_level || 0;
  const isBreached: boolean = doc.agreement_status === "Failed";
  if (!isBreached && level === 0) return { visible: false };

  const since = doc.mcx_last_escalated_on
    ? dayjs(doc.mcx_last_escalated_on).fromNow()
    : null;

  if (level >= 3) {
    return {
      visible: true,
      title: "Escalated to Country Head",
      badge: "L3 — Country Head",
      badgeTheme: "red",
      wrapClass: "border-red-200 bg-red-50",
      iconClass: "text-red-500",
      textClass: "text-red-700",
      since,
    };
  }
  if (level === 2) {
    return {
      visible: true,
      title: "Escalated to Department Head",
      badge: "L2 — Dept. Head",
      badgeTheme: "red",
      wrapClass: "border-red-200 bg-red-50",
      iconClass: "text-red-500",
      textClass: "text-red-700",
      since,
    };
  }
  if (level === 1) {
    return {
      visible: true,
      title: "Escalated to Supervisor",
      badge: "L1 — Supervisor",
      badgeTheme: "orange",
      wrapClass: "border-orange-200 bg-orange-50",
      iconClass: "text-orange-500",
      textClass: "text-orange-700",
      since,
    };
  }
  // SLA failed but the 15-min job hasn't fired yet
  return {
    visible: true,
    title: "SLA Breached",
    badge: "Pending Escalation",
    badgeTheme: "orange",
    wrapClass: "border-orange-200 bg-orange-50",
    iconClass: "text-orange-500",
    textClass: "text-orange-700",
    since: null,
  };
});
const activities = inject(ActivitiesSymbol)!;
const recentSimilarTickets = inject(RecentSimilarTicketsSymbol)!;
const { getFields, getField } = getMeta("HD Ticket");
const { notifyTicketUpdate } = useNotifyTicketUpdate(ticket.value?.name);

const dateFormat = window.date_format;
const { getStatus, colorMap } = useTicketStatusStore();

// ticket_type, sub_issue_type, priority, customer, agent_group
const coreFields = computed(() => {
  const fieldsMeta = getFields();
  if (!fieldsMeta || fieldsMeta.length === 0) {
    return [];
  }

  const ticketTypeField = getField("ticket_type");
  const subIssueField = getSubIssueFieldMeta();
  const _coreFields = [
    { group: false, fields: [ticketTypeField].filter(Boolean) },
    ...(subIssueField ? [{ group: false, fields: [subIssueField] }] : []),
    { group: true, fields: [getField("priority")].filter(Boolean) },
    { group: false, fields: [getField("customer")].filter(Boolean) },
    { group: true, fields: [getField("agent_group")].filter(Boolean) },
  ];

  _coreFields.forEach((section) => {
    section.fields = section.fields.map((f) => {
      f = parseField(f, ticket.value.doc);

      // cant handle required depends on as we directly set the value in DB on change
      f["required"] = f.reqd;
      f["ref"] = f.fieldname;

      f = getFieldInFormat(f, f);
      if (f.fieldname === "sub_issue_type") {
        f["visible"] = !!ticket.value.doc.ticket_type && !f.hidden;
        f["filters"] = ticket.value.doc.ticket_type
          ? [["issue_type", "=", ticket.value.doc.ticket_type]]
          : null;
      } else {
        f["visible"] = true;
      }
      return f;
    });
  });
  return _coreFields;
});

function getSubIssueFieldMeta() {
  const field = getField("sub_issue_type");
  if (field) return field;

  const customField = customizations.value.data?.custom_fields?.find(
    (f) => f.fieldname === "sub_issue_type"
  );
  if (!customField) return null;

  return {
    fieldname: "sub_issue_type",
    label: "Sub Issue Type",
    fieldtype: "Link",
    options: "HD Sub Issue Type",
    read_only: 0,
    hidden: 0,
    depends_on: "eval:doc.ticket_type",
    reqd: 0,
    ...customField,
  };
}

const customFields = computed(() => {
  const fieldsMeta = getFields();
  if (!fieldsMeta || fieldsMeta.length === 0) {
    return [];
  }

  if (!customizations.value.data || customizations.value.loading) return [];
  let customFields = customizations.value.data?.custom_fields || [];
  const _coreFields = [
    "ticket_type",
    "sub_issue_type",
    "priority",
    "customer",
    "agent_group",
    "subject",
    "status",
  ];
  customFields = customFields.filter((f) => !_coreFields.includes(f.fieldname));
  let _customFields = customFields
    .map((f) => {
      let fieldMeta = getField(f.fieldname);
      if (!fieldMeta) return null;

      fieldMeta = parseField(fieldMeta, ticket.value.doc);
      // cant handle required depends on as we directly set the value in DB
      fieldMeta["required"] = fieldMeta.reqd || f.required;

      return getFieldInFormat(f, fieldMeta);
    })
    .filter(Boolean);
  return _customFields;
});

const openedSections = useStorage(
  "openedSections",
  {
    ticketInfo: false,
    recentTickets: false,
    similarTickets: false,
  },
  localStorage,
  { mergeDefaults: true }
);

const sections = computed(() => {
  if (recentSimilarTickets.value.loading || !recentSimilarTickets.value.data) {
    return [];
  }
  const recentTickets = recentSimilarTickets.value?.data?.recent_tickets || [];
  const similarTickets =
    recentSimilarTickets.value?.data?.similar_tickets || [];
  const _sections = [];
  if (recentTickets.length) {
    _sections.push({
      key: "recentTickets" as const,
      label: "Recent Tickets",
      tooltipMessage: "Tickets recently raised by this contact/customer",
      hideLabel: false,
      tickets: recentTickets,
    });
  }
  if (similarTickets.length) {
    _sections.push({
      key: "similarTickets" as const,
      label: "Similar Tickets",
      tooltipMessage: "Tickets with similar queries",
      hideLabel: false,
      tickets: similarTickets,
    });
  }
  return _sections;
});

function getStatusColor(status: string) {
  const { color } = getStatus(status) ?? {};
  return colorMap[color] ?? colorMap["Default"];
}

function formatDate(date: string) {
  return dayjs(date).format(dateFormat.toUpperCase());
}

function openTicket(name: string) {
  let url = window.location.origin + "/helpdesk/tickets/" + name;
  window.open(url, "_blank");
}

function getFieldInFormat(fieldTemplate, fieldMeta) {
  return {
    label: fieldMeta?.label || fieldTemplate.fieldname,
    value: ticket.value.doc[fieldTemplate.fieldname],
    fieldtype: fieldMeta?.fieldtype,
    doctype: fieldMeta?.options || "",
    options: fieldMeta?.options || "",
    placeholder:
      fieldTemplate.placeholder ||
      `Enter ${fieldMeta?.label || fieldTemplate.fieldname}`,
    readonly: Boolean(fieldMeta.read_only),
    disabled: Boolean(fieldMeta.read_only),
    url_method: fieldTemplate.url_method || "",
    fieldname: fieldTemplate.fieldname,
    required: fieldTemplate.required || fieldMeta?.required || false,
    visible:
      fieldMeta.display_via_depends_on &&
      !fieldMeta.hidden &&
      (!!ticket.value.doc[fieldTemplate.fieldname] || !fieldMeta.read_only),
  };
}

const normalize = (v: string | FieldValue) =>
  v === null || v === undefined ? "" : v;

function handleFieldUpdate(
  fieldname: string,
  value: FieldValue,
  isCoreFieldUpdated = false
) {
  if (normalize(ticket.value.doc[fieldname]) == normalize(value)) return;
  if (isCoreFieldUpdated) {
    const label = getField(fieldname)?.label || fieldname;
    notifyTicketUpdate(label, value as string);
  }
  const updates: Record<string, FieldValue> = { [fieldname]: value };
  if (fieldname === "ticket_type") {
    updates.sub_issue_type = "";
  }
  ticket.value.setValue.submit(updates, {
    onSuccess: () => {
      if (fieldname === "agent_group") {
        assignees.value.reload();
      }
      activities.value.reload();
    },
  });
}

const fieldRefs = ref<Record<string, any>>({});

const setFieldRef = (fieldname: string, el: any) => {
  if (el) {
    fieldRefs.value[fieldname] = el;
  }
};

const showRecentSimilarTickets = computed(() => {
  return (
    !recentSimilarTickets.value.loading &&
    (recentSimilarTickets.value?.data?.recent_tickets?.length ||
      recentSimilarTickets.value?.data?.similar_tickets?.length)
  );
});

useShortcut("t", () => {
  fieldRefs.value?.ticket_type?.$el?.querySelector("button")?.click();
});

useShortcut("p", () => {
  fieldRefs.value?.priority?.$el?.querySelector("button")?.click();
});

useShortcut({ key: "t", shift: true }, () => {
  fieldRefs.value?.agent_group?.$el?.querySelector("button")?.click();
});
</script>

<style scoped>
:deep(.form-control-core button) {
  @apply text-base rounded h-7 py-1.5 border border-outline-gray-2 bg-surface-white placeholder-ink-gray-4 hover:border-outline-gray-3 hover:shadow-sm focus:bg-surface-white focus:border-outline-gray-4 focus:shadow-sm focus:ring-0 focus-visible:ring-0 text-ink-gray-8 transition-colors w-full dark:[color-scheme:dark];
}
:deep(.form-control-core button > div) {
  @apply truncate;
}

:deep(.form-control-core div) {
  width: 100%;
  display: flex;
}
</style>
