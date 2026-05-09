<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import CandidateIssues from '$lib/components/CandidateIssues.svelte';
  import DetailSidebar from '$lib/components/DetailSidebar.svelte';
  import MetricGrid from '$lib/components/MetricGrid.svelte';
  import PromptDock from '$lib/components/PromptDock.svelte';
  import ReportPanel from '$lib/components/ReportPanel.svelte';
  import ServiceMap from '$lib/components/ServiceMap.svelte';
  import StudioHeader from '$lib/components/StudioHeader.svelte';
  import { sampleAssessment, severityOrder } from '$lib/assessment';
  import type { ClusterAssessment, IncidentAssessment, Severity } from '$lib/assessment';
  import { buildServiceNodes, readableCause, readableTitle, resourceType, type StudioTab } from '$lib/studio';

  type ViewState = 'ready' | 'loading' | 'error';

  let viewState = $state<ViewState>('ready');
  let assessment = $state<ClusterAssessment>(sampleAssessment);
  let selectedIncidentIndex = $state(0);
  let commandCopied = $state(false);
  let liveSource = $state('sample context');
  let errorMessage = $state('');
  let hasLoadedLiveAssessment = $state(false);
  let isRefreshing = $state(false);
  let activeTab = $state<StudioTab>('chain');

  const activeIncidents = $derived(
    [...assessment.incidents].sort((a, b) => severityOrder[b.severity] - severityOrder[a.severity])
  );
  const selectedIncident = $derived<IncidentAssessment | null>(
    activeIncidents[selectedIncidentIndex] ?? activeIncidents[0] ?? null
  );
  const selectedEvidence = $derived(selectedIncident?.evidence ?? []);
  const affectedResourceCount = $derived(
    new Set(activeIncidents.flatMap((incident) => incident.affected_resources)).size
  );
  const highSeverityCount = $derived(
    activeIncidents.filter((incident) => ['critical', 'high'].includes(incident.severity)).length
  );
  const namespaces = $derived(
    Array.from(new Set(activeIncidents.flatMap((incident) => incident.evidence.map((evidence) => evidence.namespace)).filter(Boolean)))
  );
  const sourceNames = $derived(
    Array.from(new Set(activeIncidents.flatMap((incident) => incident.evidence.map((evidence) => evidence.source)))).slice(0, 4)
  );
  const serviceNodes = $derived(buildServiceNodes(activeIncidents));
  const metrics = $derived([
    { label: 'Evidence signals', value: Intl.NumberFormat('en').format(assessment.evidence_count) },
    { label: 'Candidate issues', value: activeIncidents.length.toString() },
    { label: 'Affected resources', value: affectedResourceCount.toString() },
    { label: 'High severity', value: highSeverityCount.toString() },
    { label: 'Unknowns', value: assessment.unknowns.length.toString() },
    { label: 'Namespaces', value: namespaces.length ? namespaces.join(', ') : 'cluster' }
  ]);
  const commandPreview = $derived(selectedIncident?.safe_next_steps[0] ?? 'sre-cli assess --context-file context.json');
  const selectedTitle = $derived(selectedIncident ? readableTitle(selectedIncident) : 'No candidate issue selected');
  const selectedCause = $derived(selectedIncident ? readableCause(selectedIncident) : 'No action needed right now.');
  const selectedResource = $derived(selectedIncident?.affected_resources[0] ?? 'unknown');
  const selectedFacts = $derived([
    { label: 'Resource', value: selectedResource },
    { label: 'Namespace', value: selectedEvidence[0]?.namespace ?? 'cluster' },
    { label: 'Type', value: resourceType(selectedResource) },
    { label: 'Severity', value: selectedIncident ? selectedIncident.severity.toUpperCase() : 'UNKNOWN' }
  ]);

  onMount(() => {
    void refreshAssessment();
  });

  async function refreshAssessment() {
    if (hasLoadedLiveAssessment) {
      isRefreshing = true;
    } else {
      viewState = 'loading';
    }
    errorMessage = '';
    try {
      const response = await fetch('/api/assessment');
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error ?? 'Unable to load assessment');
      }
      assessment = payload.assessment;
      liveSource = `${payload.source} / ${payload.namespace}`;
      selectedIncidentIndex = 0;
      hasLoadedLiveAssessment = true;
      viewState = 'ready';
      await tick();
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Unable to load assessment';
      if (!hasLoadedLiveAssessment) {
        viewState = 'error';
      }
    } finally {
      isRefreshing = false;
    }
  }

  function selectIncident(index: number) {
    selectedIncidentIndex = index;
    commandCopied = false;
  }

  async function copyCommand() {
    commandCopied = true;
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(commandPreview);
    }
  }
</script>

<svelte:head>
  <title>Octobot Studio</title>
  <meta name="description" content="Octobot Kubernetes incident triage studio." />
</svelte:head>

<main class="octobot-shell min-h-[100dvh] px-6 pb-44 pt-8 text-[#171b18] sm:px-10 lg:px-14">
  <section class="mx-auto max-w-[1180px]">
        <StudioHeader activeTab={activeTab} setTab={(tab) => (activeTab = tab)} />

        {#if viewState === 'loading'}
          <section class="grid gap-5 lg:grid-cols-[1fr_18rem]" transition:fade={{ duration: 160 }}>
            <div class="grid gap-4 sm:grid-cols-2">
              {#each Array.from({ length: 6 }) as _, index (index)}
                <div
                  class="h-20 animate-pulse rounded-lg border border-[#e1e5df] bg-[#f6f8f5]"
                  style={`animation-delay: ${index * 70}ms`}
                  transition:fly={{ y: 10, duration: 180, delay: index * 25, easing: cubicOut }}
                ></div>
              {/each}
            </div>
            <div class="h-48 animate-pulse rounded-lg border border-[#e1e5df] bg-[#f6f8f5]"></div>
          </section>
        {:else if viewState === 'error'}
          <section class="rounded-lg border border-[#e2a29a] bg-[#fff2f0] p-4 text-[#8e372d]" transition:fly={{ y: 8, duration: 180, easing: cubicOut }}>
            <p class="font-semibold">Assessment unavailable</p>
            <p class="mt-2 text-sm leading-6">{errorMessage}</p>
          </section>
        {:else}
          <section class="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]" transition:fade={{ duration: 160 }}>
            <div class="min-w-0">
              <MetricGrid {metrics} {sourceNames} />
              <ReportPanel {activeTab} {assessment} {activeIncidents} {selectedCause} {highSeverityCount} {affectedResourceCount} />
              <ServiceMap {serviceNodes} />
              <CandidateIssues {activeIncidents} {selectedIncidentIndex} {selectIncident} {liveSource} />
            </div>

            <DetailSidebar
              {assessment}
              {activeIncidents}
              {selectedIncident}
              {selectedEvidence}
              {selectedFacts}
              {selectedTitle}
              {selectedCause}
              {commandCopied}
              {commandPreview}
              {hasLoadedLiveAssessment}
              {sourceNames}
              {copyCommand}
            />
          </section>

        {/if}
  </section>
  <PromptDock />
</main>
