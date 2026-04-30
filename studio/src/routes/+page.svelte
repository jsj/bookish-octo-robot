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
  const metrics = $derived([
    { label: 'Open incidents', value: activeIncidents.length.toString() },
    { label: 'High risk', value: highSeverityCount.toString() },
    { label: 'Affected resources', value: affectedResourceCount.toString() },
    { label: 'Evidence signals', value: assessment.evidence_count.toString() }
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

<main class="ops-grid min-h-[100dvh] bg-[#080b10] px-4 py-4 text-slate-200 sm:px-6">
  <section class="mx-auto grid max-w-[1500px] gap-4 xl:grid-cols-[22rem_1fr]">
    <aside class="rounded-xl border border-slate-500/15 bg-[#0b1017]/95 p-4 shadow-2xl shadow-black/20">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="mono text-[0.65rem] uppercase tracking-[0.28em] text-[#c9912b]">SITUATION ROOM</p>
          <h1 class="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-100">Current cluster</h1>
        </div>
        <span class={`mono border px-2.5 py-1 text-[0.68rem] uppercase tracking-[0.18em] ${severityClasses(assessment.severity)}`}>
          {assessment.severity}
        </span>
      </div>

      <p class="mt-5 text-sm leading-6 text-slate-400">
        The home base for cluster incidents: current state, affected systems, evidence, and the next safe action.
      </p>

      <div class="mt-6 rounded-lg border border-slate-500/15 bg-[#080c12] p-3">
        <p class="mono text-[0.62rem] uppercase tracking-[0.22em] text-slate-500">Source</p>
        <p class="mono mt-2 break-all text-xs leading-5 text-slate-300">{liveSource}</p>
      </div>

      <div class="mt-4 grid grid-cols-2 gap-2">
        {#each metrics as metric (metric.label)}
          <div class="rounded-lg border border-slate-500/15 bg-[#0d1219] p-3">
            <p class="mono text-[0.62rem] uppercase tracking-[0.16em] text-slate-500">{metric.label}</p>
            <p class="mono mt-2 text-2xl text-slate-100">{metric.value}</p>
          </div>
        {/each}
      </div>

      <button class="mt-4 w-full rounded-lg border border-[#c9912b]/45 bg-[#c9912b]/10 px-3 py-2.5 text-sm font-medium text-[#f2d18d] hover:bg-[#c9912b]/15" onclick={refreshAssessment}>
        Refresh assessment
      </button>
    </aside>

    <section class="grid min-w-0 gap-4">
      <header class="rounded-xl border border-slate-500/15 bg-[#0b1017]/95 p-4 sm:p-5">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="mono text-[0.65rem] uppercase tracking-[0.28em] text-slate-500">SITUATION ROOM</p>
            <h2 class="mt-2 max-w-4xl text-3xl font-semibold leading-none tracking-[-0.05em] text-slate-100 sm:text-4xl">
              {assessment.summary}
            </h2>
          </div>
          <button class="w-fit rounded-lg border border-slate-500/20 px-3 py-2 text-sm text-slate-300 hover:bg-white/[0.04]" onclick={refreshAssessment}>
            Re-run
          </button>
        </div>
      </header>

      {#if viewState === 'loading'}
        <div class="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <div class="space-y-2 rounded-xl border border-slate-500/15 bg-[#0d1219] p-3">
            {#each Array.from({ length: 5 }) as _, index (index)}
              <div class="h-20 animate-pulse rounded-lg bg-slate-700/20" style={`animation-delay: ${index * 70}ms`}></div>
            {/each}
          </div>
          <div class="h-[28rem] animate-pulse rounded-xl border border-slate-500/15 bg-slate-700/15"></div>
        </div>
      {:else if viewState === 'error'}
        <div class="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-100">
          <p class="mono text-xs uppercase tracking-[0.24em]">Assessment unavailable</p>
          <p class="mt-4 max-w-3xl text-xl leading-7">{errorMessage}</p>
        </div>
      {:else}
        <div class="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <section class="overflow-hidden rounded-xl border border-slate-500/15 bg-[#0d1219]/96">
            <div class="flex items-center justify-between border-b border-slate-500/15 px-4 py-3">
              <p class="mono text-xs uppercase tracking-[0.2em] text-slate-400">Incidents</p>
              <p class="text-xs text-slate-500">Highest severity first</p>
            </div>

            <div class="divide-y divide-slate-500/15">
              {#each activeIncidents as incident, index (incident.title)}
                <button class="group grid w-full grid-cols-[0.25rem_1fr] text-left" onclick={() => selectIncident(index)}>
                  <span class={[severityRail(incident.severity), selectedIncidentIndex === index ? 'opacity-100' : 'opacity-40']}></span>
                  <span class={['block px-4 py-4 transition', selectedIncidentIndex === index ? 'bg-white/[0.055]' : 'hover:bg-white/[0.03]']}>
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
          </section>

          <section class="min-w-0 overflow-hidden rounded-xl border border-slate-500/15 bg-[#101722]">
            {#if selectedIncident}
              <div class="border-b border-slate-500/15 p-4 sm:p-5">
                <p class="mono text-xs uppercase tracking-[0.2em] text-[#c9912b]">Selected</p>
                <h3 class="mt-3 max-w-4xl text-2xl font-semibold leading-tight tracking-[-0.04em] text-slate-100 sm:text-3xl">
                  {selectedIncident.title}
                </h3>
                <p class="mt-3 max-w-4xl text-sm leading-6 text-slate-400">{selectedIncident.likely_cause}</p>
              </div>

              <div class="grid gap-px bg-slate-500/15 xl:grid-cols-[1fr_19rem]">
                <div class="bg-[#101722] p-4 sm:p-5">
                  <p class="mono mb-3 text-xs uppercase tracking-[0.2em] text-slate-400">Evidence</p>
                  <div class="space-y-2">
                    {#each selectedEvidence as evidence (`${evidence.source}-${evidence.signal}-${evidence.detail}`)}
                      <div class="rounded-lg border border-slate-500/15 bg-[#0b1017] p-3">
                        <div class="flex flex-wrap items-center gap-2">
                          <span class="mono text-[0.68rem] uppercase tracking-[0.16em] text-[#5aa8b5]">{evidence.source}</span>
                          <span class="mono border border-slate-500/20 bg-slate-500/10 px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.12em] text-slate-300">{evidence.signal}</span>
                        </div>
                        <p class="mt-2 text-sm leading-6 text-slate-300">{evidence.detail}</p>
                        <p class="mono mt-2 break-all text-[0.68rem] text-slate-600">{evidence.resource}</p>
                      </div>
                    {/each}
                  </div>
                </div>

                <aside class="bg-[#0b1017] p-4 sm:p-5">
                  <p class="mono text-xs uppercase tracking-[0.2em] text-slate-400">Next step</p>
                  <pre class="mono mt-3 overflow-x-auto rounded-lg border border-[#c9912b]/25 bg-[#c9912b]/8 p-3 text-[0.74rem] leading-5 text-[#f2d18d]">{commandPreview}</pre>
                  <button class="mt-3 rounded-lg border border-slate-500/20 px-3 py-2 text-sm text-slate-300 hover:bg-white/[0.04]" onclick={copyCommand}>
                    {commandCopied ? 'Copied' : 'Copy command'}
                  </button>
                </aside>
              </div>
            {/if}
          </section>
        </div>
      {/if}
    </section>
  </section>
</main>
