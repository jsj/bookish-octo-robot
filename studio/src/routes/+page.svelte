<script lang="ts">
  import { onMount } from 'svelte';
  import { sampleAssessment, severityOrder } from '$lib/assessment';
  import type { ClusterAssessment, IncidentAssessment, Severity } from '$lib/assessment';

  type ViewState = 'ready' | 'loading' | 'error';

  let viewState = $state<ViewState>('ready');
  let assessment = $state<ClusterAssessment>(sampleAssessment);
  let selectedIncidentIndex = $state(0);
  let commandCopied = $state(false);
  let liveSource = $state('sample context');
  let errorMessage = $state('');

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
  const commandPreview = $derived(selectedIncident?.safe_next_steps[0] ?? 'sre-cli assess --context-file context.json');
  const primarySummary = $derived(
    activeIncidents.length === 0
      ? 'No active incidents.'
      : `${activeIncidents.length} incident${activeIncidents.length === 1 ? '' : 's'} need attention.`
  );
  const priorityLine = $derived(
    selectedIncident ? `Start with ${selectedIncident.title}.` : 'Cluster looks quiet.'
  );
  const metrics = $derived([
    { label: 'High risk', value: highSeverityCount.toString() },
    { label: 'Affected', value: affectedResourceCount.toString() },
    { label: 'Signals', value: assessment.evidence_count.toString() }
  ]);

  onMount(() => {
    void refreshAssessment();
  });

  async function refreshAssessment() {
    viewState = 'loading';
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
      viewState = 'ready';
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Unable to load assessment';
      viewState = 'error';
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

  function severityClasses(severity: Severity) {
    return {
      critical: 'border-red-500/70 bg-red-500/15 text-red-100',
      high: 'border-[#c9912b]/70 bg-[#c9912b]/12 text-[#f2d18d]',
      medium: 'border-[#5aa8b5]/60 bg-[#5aa8b5]/10 text-[#abd6dd]',
      low: 'border-slate-500/40 bg-slate-500/10 text-slate-300',
      info: 'border-slate-600/40 bg-slate-700/15 text-slate-400'
    }[severity];
  }

  function severityRail(severity: Severity) {
    return {
      critical: 'bg-red-500',
      high: 'bg-[#c9912b]',
      medium: 'bg-[#5aa8b5]',
      low: 'bg-slate-500',
      info: 'bg-slate-600'
    }[severity];
  }
</script>

<svelte:head>
  <title>SITUATION ROOM</title>
  <meta name="description" content="SITUATION ROOM for Kubernetes incident assessment." />
</svelte:head>

<main class="min-h-[100dvh] bg-[#080b10] px-4 py-5 text-slate-200 sm:px-6">
  <section class="mx-auto grid max-w-[1440px] gap-5">
    <header class="flex flex-col gap-4 border-b border-slate-500/15 pb-5 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="mono text-[0.68rem] uppercase tracking-[0.3em] text-[#c9912b]">SITUATION ROOM</p>
        <h1 class="mt-2 text-4xl font-semibold leading-none tracking-[-0.055em] text-slate-100 sm:text-6xl">
          {primarySummary}
        </h1>
        <p class="mt-3 max-w-3xl text-base leading-7 text-slate-400">{priorityLine}</p>
      </div>

      <div class="flex flex-col gap-2 lg:items-end">
        <span class="mono max-w-[34rem] truncate text-xs text-slate-500">{liveSource}</span>
        <button class="w-fit rounded-lg border border-slate-500/20 bg-white/[0.03] px-3 py-2 text-sm text-slate-300 hover:bg-white/[0.06]" onclick={refreshAssessment}>
          Refresh
        </button>
      </div>
    </header>

    {#if viewState === 'loading'}
      <section class="grid gap-5 lg:grid-cols-[0.78fr_1.22fr]">
        <div class="space-y-2 rounded-2xl border border-slate-500/15 bg-[#0d1219] p-3">
          {#each Array.from({ length: 5 }) as _, index (index)}
            <div class="h-20 animate-pulse rounded-xl bg-slate-700/20" style={`animation-delay: ${index * 70}ms`}></div>
          {/each}
        </div>
        <div class="h-[30rem] animate-pulse rounded-2xl border border-slate-500/15 bg-slate-700/15"></div>
      </section>
    {:else if viewState === 'error'}
      <section class="rounded-2xl border border-red-500/30 bg-red-500/10 p-6 text-red-100">
        <p class="mono text-xs uppercase tracking-[0.24em]">Assessment unavailable</p>
        <p class="mt-4 max-w-3xl text-xl leading-7">{errorMessage}</p>
      </section>
    {:else}
      <section class="grid gap-5 lg:grid-cols-[0.78fr_1.22fr]">
        <aside class="rounded-2xl border border-slate-500/15 bg-[#0b1017]/95 p-4 shadow-2xl shadow-black/20">
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-lg font-semibold tracking-[-0.03em] text-slate-100">Incidents</h2>
            <span class={`mono border px-2.5 py-1 text-[0.68rem] uppercase tracking-[0.18em] ${severityClasses(assessment.severity)}`}>
              {assessment.severity}
            </span>
          </div>

          <div class="mt-4 grid grid-cols-3 gap-2">
            {#each metrics as metric (metric.label)}
              <div class="rounded-xl border border-slate-500/15 bg-[#0d1219] p-3">
                <p class="mono text-[0.62rem] uppercase tracking-[0.14em] text-slate-500">{metric.label}</p>
                <p class="mono mt-2 text-2xl text-slate-100">{metric.value}</p>
              </div>
            {/each}
          </div>

          <div class="mt-4 overflow-hidden rounded-xl border border-slate-500/15">
            {#each activeIncidents as incident, index (incident.title)}
              <button class="group grid w-full grid-cols-[0.25rem_1fr] border-b border-slate-500/15 text-left last:border-b-0" onclick={() => selectIncident(index)}>
                <span class={[severityRail(incident.severity), selectedIncidentIndex === index ? 'opacity-100' : 'opacity-40']}></span>
                <span class={['block px-4 py-4 transition', selectedIncidentIndex === index ? 'bg-white/[0.06]' : 'bg-[#0d1219] hover:bg-white/[0.035]']}>
                  <span class="flex flex-wrap items-center justify-between gap-3">
                    <span class={`mono border px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.16em] ${severityClasses(incident.severity)}`}>{incident.severity}</span>
                    <span class="text-xs text-slate-500">{incident.evidence.length} signals</span>
                  </span>
                  <span class="mt-3 block text-base font-medium tracking-[-0.025em] text-slate-100">{incident.title}</span>
                  <span class="mt-2 line-clamp-2 block text-sm leading-5 text-slate-400">{incident.likely_cause}</span>
                </span>
              </button>
            {/each}
          </div>
        </aside>

        <section class="min-w-0 overflow-hidden rounded-2xl border border-slate-500/15 bg-[#101722] shadow-2xl shadow-black/20">
          {#if selectedIncident}
            <div class="border-b border-slate-500/15 p-5 sm:p-6">
              <div class="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                <div class="min-w-0">
                  <p class="mono text-xs uppercase tracking-[0.2em] text-[#c9912b]">Selected incident</p>
                  <h2 class="mt-3 max-w-4xl text-3xl font-semibold leading-tight tracking-[-0.045em] text-slate-100 sm:text-4xl">
                    {selectedIncident.title}
                  </h2>
                  <p class="mt-4 max-w-3xl text-base leading-7 text-slate-400">{selectedIncident.likely_cause}</p>
                </div>

                <div class="w-full rounded-xl border border-[#c9912b]/25 bg-[#c9912b]/8 p-3 xl:w-[23rem]">
                  <p class="mono text-[0.66rem] uppercase tracking-[0.18em] text-[#f2d18d]/75">Next safe command</p>
                  <pre class="mono mt-2 overflow-x-auto whitespace-pre-wrap text-[0.74rem] leading-5 text-[#f2d18d]">{commandPreview}</pre>
                  <button class="mt-3 rounded-lg border border-[#c9912b]/25 px-3 py-2 text-sm text-[#f2d18d] hover:bg-[#c9912b]/10" onclick={copyCommand}>
                    {commandCopied ? 'Copied' : 'Copy command'}
                  </button>
                </div>
              </div>
            </div>

            <div class="p-5 sm:p-6">
              <div class="mb-4 flex items-center justify-between gap-3">
                <p class="mono text-xs uppercase tracking-[0.2em] text-slate-400">Evidence</p>
                <p class="text-sm text-slate-500">{selectedEvidence.length} signals linked to this incident</p>
              </div>

              <div class="grid gap-3 xl:grid-cols-2">
                {#each selectedEvidence as evidence (`${evidence.source}-${evidence.signal}-${evidence.detail}`)}
                  <article class="rounded-xl border border-slate-500/15 bg-[#0b1017] p-4">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="mono text-[0.68rem] uppercase tracking-[0.16em] text-[#5aa8b5]">{evidence.source}</span>
                      <span class="mono rounded border border-slate-500/20 bg-slate-500/10 px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.12em] text-slate-300">{evidence.signal}</span>
                    </div>
                    <p class="mt-3 text-sm leading-6 text-slate-300">{evidence.detail}</p>
                    <p class="mono mt-3 break-all text-[0.68rem] text-slate-600">{evidence.resource}</p>
                  </article>
                {/each}
              </div>
            </div>
          {/if}
        </section>
      </section>
    {/if}
  </section>
</main>
