<template>
  <div class="flex h-screen w-screen">
    <MobileSidebar />
    <div class="flex h-full flex-col flex-1 overflow-auto">
      <MobileAppHeader />
      <slot />
    </div>
  </div>
</template>
<script setup>
import MobileSidebar from "@/components/layouts/MobileSidebar.vue";
import MobileAppHeader from "@/components/layouts/MobileAppHeader.vue";
</script>
