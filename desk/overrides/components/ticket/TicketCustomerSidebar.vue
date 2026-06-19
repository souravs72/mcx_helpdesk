<template>
  <div class="flex w-[382px] flex-col border-s gap-4">
    <!-- Ticket ID -->
    <div class="flex items-center justify-between border-b px-5 py-3">
      <span class="cursor-copy text-lg font-semibold">Ticket details</span>
    </div>
    <!-- user info and sla info -->
    <div class="flex flex-col gap-4 pt-0 px-5 py-3 border-b">
      <!-- user info -->
      <div class="flex gap-2">
        <Avatar
          size="2xl"
          :image="ticket.data.contact.image"
          :label="ticket.data.contact.name"
        />
        <div class="flex items-center justify-between">
          <Tooltip :text="ticket.data.contact.name">
            <div class="w-[242px] truncate text-2xl font-medium">
              {{ ticket.data.contact.name }}
            </div>
          </Tooltip>
          <div class="flex gap-1.5" v-if="!ticket.data.feedback_rating">
            <Tooltip :text="ticket.data.contact.email_id">
              <Button class="h-7 w-7" @click="emit('open')">
                <template #icon>
                  <EmailIcon class="h-4 w-4" />
                </template>
              </Button>
            </Tooltip>
          </div>
        </div>
      </div>

      <!-- Ticket Info -->
      <div
        class="flex items-center text-base leading-5"
        v-for="field in ticketBasicInfo"
      >
        <span class="w-[126px] text-sm text-ink-gray-5">{{ field.label }}</span>
        <span
          class="text-base text-ink-gray-8 flex-1"
          :class="!field.value && 'text-ink-gray-4'"
        >
          {{ field.value || "—" }}
        </span>
      </div>

      <!-- sla info -->
      <div
        v-for="data in slaData"
        :key="data.label"
        class="flex items-center text-base"
      >
        <div class="w-[126px] text-ink-gray-5 text-sm">{{ data.title }}</div>
        <div
          class="break-words text-base text-ink-gray-8 flex items-center gap-2"
        >
          <Tooltip :text="dateFormat(data.value, dateTooltipFormat)">
            <Badge :label="data.label" :theme="data.theme" variant="subtle" />
          </Tooltip>
          <!-- SLA explanation icon -->
          <Tooltip
            v-if="
              dayjs(data.value).diff(dayjs(), 'day', true) > 4 &&
              data.title === 'Resolution'
            "
            :text="
              __(
                'This date is calculated based on configured SLAs, working hours, and holidays.'
              )
            "
          >
            <lucide-circle-question-mark
              class="h-4 w-4 text-ink-gray-6 cursor-pointer"
            />
          </Tooltip>
        </div>
      </div>

      <!-- MCX: escalation indicator -->
      <div
        v-if="escalationLevel > 0"
        class="flex items-center text-base"
      >
        <div class="w-[126px] text-ink-gray-5 text-sm shrink-0">Escalation</div>
        <div class="flex items-center gap-2 flex-wrap">
          <Badge
            :label="escalationLabel"
            :theme="escalationTheme"
            variant="subtle"
          />
          <Tooltip
            :text="escalationTooltip"
          >
            <lucide-circle-question-mark class="h-4 w-4 text-ink-gray-6 cursor-pointer" />
          </Tooltip>
        </div>
      </div>
    </div>
    <!-- feedback component -->
    <TicketFeedback
      v-if="ticket.data.feedback_rating"
      class="border-b text-base text-ink-gray-5"
      :ticket="ticket.data"
    />
    <div class="flex flex-col gap-4 pt-0 px-5 py-3 overflow-y-auto">
      <div
        class="flex items-center text-base leading-5"
        v-for="field in ticketAdditionalInfo"
        :key="field.fieldname"
      >
        <span class="w-[126px] text-sm text-ink-gray-5">{{ field.label }}</span>
        <span
          class="text-base text-ink-gray-8 flex-1"
          :class="!field.value && 'text-ink-gray-4'"
        >
          <template
            v-if="
              field.value &&
              (field.fieldtype === 'Date' || field.fieldtype === 'Datetime') &&
              dayjs(field.value).isValid()
            "
          >
            {{ dateFormat(field.value, dateTooltipFormat) }}
          </template>
          <template v-else>
            {{ field.value || "—" }}
          </template>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ITicket } from "@/pages/ticket/symbols";
import { Field } from "@/types";
import { dateFormat, dateTooltipFormat, formatTime } from "@/utils";
import { Avatar, dayjs, Tooltip } from "frappe-ui";
import { computed, inject } from "vue";

const emit = defineEmits(["open"]);

const ticket = inject(ITicket);

const escalationLevel = computed(() => ticket.data.mcx_escalation_level || 0);

const escalationLabel = computed(() => {
  const level = escalationLevel.value;
  if (level === 1) return "Escalated to Supervisor";
  if (level === 2) return "Escalated to Dept. Head";
  if (level >= 3) return "Escalated to Country Head";
  return "";
});

const escalationTheme = computed(() => {
  const level = escalationLevel.value;
  if (level >= 2) return "red";
  return "orange";
});

const escalationTooltip = computed(() => {
  const level = escalationLevel.value;
  if (level >= 3)
    return __(
      "Your ticket has been escalated to our Country Head and is receiving the highest level of attention."
    );
  if (level === 2)
    return __(
      "Your ticket has been escalated to a Department Head for priority resolution."
    );
  return __(
    "Your ticket has been escalated to a senior team member for priority attention due to resolution time."
  );
});

const slaData = computed(() => {
  const firstResponse = firstResponseData();
  const resolution = resolutionData();
  return [
    {
      title: "First Response",
      value: ticket.data.first_responded_on || ticket.data.response_by,
      label: firstResponse.label,
      theme: firstResponse.color,
    },
    {
      title: "Resolution",
      value: ticket.data.resolution_date || ticket.data.resolution_by,
      label: resolution.label,
      theme: resolution.color,
    },
  ];
});

function firstResponseData() {
  // Paused: clock is stopped, show neutral state rather than misleading countdown.
  if (!ticket.data.first_responded_on && ticket.data.agreement_status === "Paused") {
    return { label: "Paused", color: "blue" };
  }
  if (
    !ticket.data.first_responded_on &&
    dayjs().isBefore(dayjs(ticket.data.response_by))
  ) {
    return {
      label: `Due in ${formatTime(
        dayjs(ticket.data.response_by).diff(dayjs(), "s")
      )}`,
      color: "orange",
    };
  } else if (
    dayjs(ticket.data.first_responded_on).isBefore(
      dayjs(ticket.data.response_by)
    )
  ) {
    return {
      label: `Fulfilled in ${formatTime(
        dayjs(ticket.data.first_responded_on).diff(
          dayjs(ticket.data.creation),
          "s"
        )
      )}`,
      color: "green",
    };
  } else {
    return { label: "Failed", color: "red" };
  }
}

function resolutionData() {
  // Paused: SLA clock is stopped, show neutral state.
  if (!ticket.data.resolution_date && ticket.data.agreement_status === "Paused") {
    return { label: "Paused", color: "blue" };
  }
  if (
    !ticket.data.resolution_date &&
    dayjs().isBefore(ticket.data.resolution_by)
  ) {
    return {
      label: `Due in ${formatTime(
        dayjs(ticket.data.resolution_by).diff(dayjs(), "s")
      )}`,
      color: "orange",
    };
  } else if (ticket.data.agreement_status === "Fulfilled") {
    // resolution_time is stored as seconds (integer) — pass directly, not via dayjs.
    return {
      label: `Fulfilled in ${formatTime(ticket.data.resolution_time)}`,
      color: "green",
    };
  } else {
    return { label: "Failed", color: "red" };
  }
}

const ticketBasicInfo = computed(() => [
  {
    label: "Ticket ID",
    value: ticket.data.name,
  },
  {
    label: "Status",
    value: ticket.data.status,
    bold: true,
  },
]);

const ticketAdditionalInfo = computed(() => {
  const templateFields: Field[] = ticket.data.template?.fields || [];

  // Build a lookup of which fields are hidden from customers via template settings.
  const hiddenFromCustomer = new Set(
    templateFields
      .filter((f: Field) => f.hide_from_customer)
      .map((f: Field) => f.fieldname)
  );

  // Hardcoded fields: respect template-level hide_from_customer.
  // agent_group maps to fieldname "agent_group" in HD Ticket (displayed as "Team").
  const hardcoded: Array<{ fieldname: string; label: string; value: string }> = [];
  if (!hiddenFromCustomer.has("subject")) {
    hardcoded.push({ fieldname: "subject", label: "Subject", value: ticket.data.subject });
  }
  if (!hiddenFromCustomer.has("agent_group")) {
    hardcoded.push({ fieldname: "agent_group", label: "Team", value: ticket.data.agent_group || "-" });
  }
  if (!hiddenFromCustomer.has("priority")) {
    hardcoded.push({ fieldname: "priority", label: "Priority", value: ticket.data.priority });
  }

  // Additional template-defined custom fields.
  const custom_fields = templateFields
    .filter(
      (field: Field) =>
        !field.hide_from_customer &&
        !["subject", "agent_group", "priority"].includes(field.fieldname)
    )
    .map((field: Field) => {
      const option = {
        label: field.label,
        value: ticket.data[field.fieldname],
        fieldtype: field.fieldtype,
      };
      if (field.fieldtype === "Date") {
        option.value = dayjs(option.value).format(
          window.date_format.toUpperCase()
        );
      }
      if (field.fieldtype === "Datetime") {
        option.value = dayjs(option.value).format(
          `${window.date_format.toUpperCase()} ${window.time_format}`
        );
      }
      return option;
    });

  return [...hardcoded, ...custom_fields];
});
</script>

<style scoped></style>
