import LucideBookOpen from "~icons/lucide/book-open";
import LucideContact2 from "~icons/lucide/contact-2";
import LucideTicket from "~icons/lucide/ticket";
import LucideLayoutDashboard from "~icons/lucide/layout-dashboard";
import LucideRadio from "~icons/lucide/radio";
import { OrganizationsIcon } from "@/components/icons";
import PhoneIcon from "@/components/icons/PhoneIcon.vue";
import { __ } from "@/translation";

/** MCX agent sidebar — Dashboard is the landing page; Home widget grid removed. */
export const agentPortalSidebarOptions = [
  {
    label: __("Dashboard"),
    icon: LucideLayoutDashboard,
    to: "Dashboard",
  },
  {
    label: __("Tickets"),
    icon: LucideTicket,
    to: "TicketsAgent",
  },
  {
    label: __("Knowledge Base"),
    icon: LucideBookOpen,
    to: "AgentKnowledgeBase",
  },
  {
    label: __("Customers"),
    icon: OrganizationsIcon,
    to: "CustomerList",
  },
  {
    label: __("Contacts"),
    icon: LucideContact2,
    to: "ContactList",
  },
  {
    label: __("Call Logs"),
    icon: PhoneIcon,
    to: "CallLogs",
  },
];

/** Manager-only sidebar entries */
export const managerPortalSidebarOptions = [
  {
    label: __("Live Queue"),
    icon: LucideRadio,
    to: "SupervisorBoard",
  },
];

export const customerPortalSidebarOptions = [
  {
    label: __("Tickets"),
    icon: LucideTicket,
    to: "TicketsCustomer",
  },
  {
    label: __("Knowledge Base"),
    icon: LucideBookOpen,
    to: "CustomerKnowledgeBase",
  },
];
