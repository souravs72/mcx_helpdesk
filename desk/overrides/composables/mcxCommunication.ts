import type { InjectionKey, Ref } from "vue";

export type CommunicationAreaHandle = {
  insertDraftReply?: (text: string) => void;
  toggleEmailBox?: () => void;
  replyToEmail?: (data: object) => void;
};

export const CommunicationAreaSymbol = Symbol(
  "communicationArea"
) as InjectionKey<Ref<CommunicationAreaHandle | null>>;
