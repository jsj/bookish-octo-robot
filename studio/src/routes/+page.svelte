<script lang="ts">
  import { sampleAssessment, severityOrder, timeline } from '$lib/assessment';
  import type { ClusterAssessment, IncidentAssessment, Severity } from '$lib/assessment';

  type ViewState = 'ready' | 'loading' | 'empty' | 'error';

  let viewState = $state<ViewState>('ready');
  let assessment = $state<ClusterAssessment>(sampleAssessment);
  let selectedIncidentIndex = $state(0);
  let commandCopied = $state(false);

  const activeIncidents = $derived(
    [...assessment.incidents].sort((a, b) => severityOrder[b.severity] - severityOrder[a.severity])
  );
  const selectedIncident = $derived<IncidentAssessment | null>(
    activeIncidents[selectedIncidentIndex] ?? activeIncidents[0] ?? null
  );
  const blastRadius = $derived(
    new Set(activeIncidents.flatMap((incident) => incident.affected_resources)).size
  );
  const highSeverityCount = $derived(
    activeIncidents.filter((incident) => ['critical', 'high'].includes(incident.severity)).length
  );
  const commandPreview = $derived(selectedIncident?.safe_next_steps[0] ?? 'sre-cli assess --context-file context.json');
  const metrics = $derived([
    { label: 'Incidents', value: activeIncidents.length.toString() },
    { label: 'High risk', value: highSeverityCount.toString() },
    { label: 'Resources', value: blastRadius.toString() },
    { label: 'Unknowns', value: assessment.unknowns.length.toString() }
  ]);

  function selectIncident(index: number) {
    selectedIncidentIndex = index;
    commandCopied = false;
  }

  function simulateRefresh() {
    viewState = 'loading';
    window.setTimeout(() => {
      assessment = sampleAssessment;
      selectedIncidentIndex = 0;
      viewState = 'ready';
    }, 760);
  }

  function showEmpty() {
    viewState = 'empty';
  }

  function showError() {
    viewState = 'error';
  }

  async function copyCommand() {
    commandCopied = true;
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(commandPreview);
    }
  }

  function severityClasses(severity: Severity) {
    return {
      critical: 'bg-red-950 text-red-50 border-red-900',
      high: 'bg-[#1a3f3c] text-white border-[#1a3f3c]',
      medium: 'bg-[#e6f0e8] text-[#1a3f3c] border-[#b7cbbd]',
      low: 'bg-white text-zinc-700 border-zinc-200',
      info: 'bg-zinc-100 text-zinc-600 border-zinc-200'
    }[severity];
  }
</script>

<svelte:head>
  <title>SRE Studio</title>
  <meta
    name="description"
    content="Local evidence-first incident studio for Kubernetes SRE assessment."
  />
</svelte:head>

<main class="soft-grid min-h-[100dvh] overflow-hidden px-4 py-5 text-[#0f1714] sm:px-6 lg:px-8">
  <section class="mx-auto grid max-w-[1500px] gap-5 lg:grid-cols-[0.78fr_1.35fr]">
    <aside
      class="relative rounded-[2rem] border border-black/10 bg-[#10201e] p-5 text-white shadow-[0_22px_60px_-28px_rgba(16,32,30,0.7)] sm:p-7 lg:min-h-[calc(100dvh-2.5rem)]"
    >
      <div class="absolute inset-x-8 top-0 h-px bg-white/35"></div>
      <nav class="flex items-center justify-between gap-4 text-sm text-white/72">
        <div class="flex items-center gap-2">
          <span class="h-2.5 w-2.5 rounded-full bg-[#16a34a] shadow-[0_0_0_4px_rgba(22,163,74,0.18)]"></span>
          <span class="mono uppercase tracking-[0.24em]">Local studio</span>
        </div>
        <span class="rounded-full border border-white/12 px-3 py-1">emulator-backed</span>
      </nav>

      <div class="mt-16 max-w-[38rem] lg:mt-24">
        <p class="mono text-xs uppercase tracking-[0.34em] text-[#a7c6ad]">Conscientious cluster guardian</p>
        <h1 class="mt-5 text-5xl font-normal leading-[0.94] tracking-[-0.07em] text-white sm:text-6xl xl:text-7xl">
          An incident room, not a chat room.
        </h1>
        <p class="mt-6 max-w-[34rem] text-base leading-7 text-white/68">
          Inspired by Traversal's enterprise AI SRE posture: causal evidence, production context,
          root-cause confidence, and safe next moves. Built locally for the FOSS Kubernetes path.
        </p>
      </div>

      <div class="mt-10 grid grid-cols-2 gap-3">
        <div class="rounded-[1.4rem] border border-white/10 bg-white/[0.06] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]">
          <p class="mono text-xs uppercase tracking-[0.2em] text-white/48">Highest severity</p>
          <p class="mt-3 text-3xl tracking-[-0.05em]">{assessment.severity}</p>
        </div>
        <div class="rounded-[1.4rem] border border-white/10 bg-white/[0.06] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]">
          <p class="mono text-xs uppercase tracking-[0.2em] text-white/48">Evidence</p>
          <p class="mono mt-3 text-3xl">{assessment.evidence_count}</p>
        </div>
      </div>

      <div class="mt-10 flex flex-wrap gap-3">
        <button
          class="rounded-full bg-white px-4 py-2.5 text-sm text-[#10201e] hover:bg-[#e6f0e8]"
          onclick={simulateRefresh}
        >
          Run local assessment
        </button>
        <button
          class="rounded-full border border-white/12 px-4 py-2.5 text-sm text-white/78 hover:bg-white/10"
          onclick={showEmpty}
        >
          Empty state
        </button>
        <button
          class="rounded-full border border-white/12 px-4 py-2.5 text-sm text-white/78 hover:bg-white/10"
          onclick={showError}
        >
          Error state
        </button>
      </div>
    </aside>

    <section class="grid gap-5">
      <div class="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <section class="rounded-[2rem] border border-black/10 bg-white/80 p-5 shadow-[0_22px_60px_-34px_rgba(15,23,20,0.35)] backdrop-blur sm:p-7">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p class="mono text-xs uppercase tracking-[0.28em] text-zinc-500">Production world model</p>
              <h2 class="mt-3 max-w-[34rem] text-3xl font-normal leading-none tracking-[-0.055em] sm:text-5xl">
                {assessment.summary}
              </h2>
            </div>
            <div class="rounded-full border px-3 py-1.5 text-sm {severityClasses(assessment.severity)}">
              {assessment.severity}
            </div>
          </div>

          {#if viewState === 'loading'}
            <div class="mt-8 space-y-3">
              {#each Array.from({ length: 4 }) as _, index (index)}
                <div
                  class="h-16 animate-pulse rounded-2xl bg-zinc-200/75"
                  style={`animation-delay: ${index * 90}ms`}
                ></div>
              {/each}
            </div>
          {:else if viewState === 'empty'}
            <div class="mt-8 rounded-[1.5rem] border border-dashed border-zinc-300 bg-zinc-50 p-8">
              <p class="mono text-xs uppercase tracking-[0.28em] text-zinc-500">No active candidates</p>
              <p class="mt-4 max-w-[30rem] text-2xl leading-tight tracking-[-0.04em]">
                The cluster assessment returned no incident candidates. Keep the heartbeat running and watch for deltas.
              </p>
            </div>
          {:else if viewState === 'error'}
            <div class="mt-8 rounded-[1.5rem] border border-red-200 bg-red-50 p-8 text-red-950">
              <p class="mono text-xs uppercase tracking-[0.28em]">Assessment unavailable</p>
              <p class="mt-4 max-w-[30rem] text-2xl leading-tight tracking-[-0.04em]">
                The studio could not reach the local assessment source. Start the emulator or pass a context file.
              </p>
            </div>
          {:else}
            <div class="mt-8 divide-y divide-zinc-200/80">
              {#each activeIncidents as incident, index (incident.title)}
                <button
                  class={[
                    'group grid w-full gap-4 py-5 text-left transition sm:grid-cols-[1fr_auto]',
                    selectedIncidentIndex === index && 'rounded-[1.25rem] bg-[#f1f1ef] px-4'
                  ]}
                  onclick={() => selectIncident(index)}
                >
                  <span>
                    <span class="flex flex-wrap items-center gap-3">
                      <span class="rounded-full border px-2.5 py-1 text-xs {severityClasses(incident.severity)}">
                        {incident.severity}
                      </span>
                      <span class="mono text-xs uppercase tracking-[0.22em] text-zinc-500">
                        {incident.evidence.length} signals
                      </span>
                    </span>
                    <span class="mt-3 block text-xl tracking-[-0.035em] text-zinc-950">{incident.title}</span>
                    <span class="mt-2 block max-w-[42rem] text-sm leading-6 text-zinc-600">
                      {incident.likely_cause}
                    </span>
                  </span>
                  <span class="mono self-center text-sm text-zinc-400 group-hover:text-[#1a3f3c]">inspect</span>
                </button>
              {/each}
            </div>
          {/if}
        </section>

        <section class="rounded-[2rem] border border-black/10 bg-[#f8f8f6] p-5 shadow-[0_22px_60px_-34px_rgba(15,23,20,0.25)] sm:p-7">
          <p class="mono text-xs uppercase tracking-[0.28em] text-zinc-500">Blast radius</p>
          <div class="mt-5 grid grid-cols-2 gap-3">
            {#each metrics as metric (metric.label)}
              <div class="rounded-[1.35rem] border border-zinc-200 bg-white p-4">
                <p class="mono text-xs uppercase tracking-[0.2em] text-zinc-500">{metric.label}</p>
                <p class="mono mt-3 text-3xl tracking-[-0.04em] text-zinc-950">{metric.value}</p>
              </div>
            {/each}
          </div>

          <div class="mt-8">
            <p class="mono text-xs uppercase tracking-[0.28em] text-zinc-500">Causal timeline</p>
            <div class="mt-5 space-y-4">
              {#each timeline as item (item.time)}
                <div class="grid grid-cols-[5.2rem_1fr] gap-4">
                  <span class="mono text-xs text-zinc-500">{item.time}</span>
                  <span class="relative border-l border-zinc-300 pl-4 text-sm leading-5 text-zinc-700">
                    <span class="absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full bg-[#1a3f3c]"></span>
                    {item.label}
                  </span>
                </div>
              {/each}
            </div>
          </div>
        </section>
      </div>

      <section class="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <section class="rounded-[2rem] border border-black/10 bg-white/82 p-5 shadow-[0_22px_60px_-34px_rgba(15,23,20,0.28)] backdrop-blur sm:p-7">
          <p class="mono text-xs uppercase tracking-[0.28em] text-zinc-500">Evidence trail</p>
          {#if selectedIncident}
            <h2 class="mt-3 text-3xl font-normal leading-none tracking-[-0.05em]">
              {selectedIncident.title}
            </h2>
            <div class="mt-6 space-y-3">
              {#each selectedIncident.evidence as evidence (`${evidence.source}-${evidence.signal}-${evidence.detail}`)}
                <div class="rounded-[1.3rem] border border-zinc-200 bg-zinc-50 p-4">
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <span class="mono text-xs uppercase tracking-[0.2em] text-zinc-500">{evidence.source}</span>
                    <span class="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-600">{evidence.signal}</span>
                  </div>
                  <p class="mt-3 text-sm leading-6 text-zinc-700">{evidence.detail}</p>
                </div>
              {/each}
            </div>
          {/if}
        </section>

        <section class="rounded-[2rem] border border-black/10 bg-[#10201e] p-5 text-white shadow-[0_22px_60px_-28px_rgba(16,32,30,0.55)] sm:p-7">
          <div class="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p class="mono text-xs uppercase tracking-[0.28em] text-white/45">Safe next action</p>
              <h2 class="mt-3 text-3xl font-normal leading-none tracking-[-0.05em]">Operator handoff</h2>
            </div>
            <button
              class="rounded-full border border-white/12 px-4 py-2 text-sm text-white/78 hover:bg-white/10"
              onclick={copyCommand}
            >
              {commandCopied ? 'Copied' : 'Copy command'}
            </button>
          </div>

          <pre class="mono mt-7 overflow-x-auto rounded-[1.35rem] border border-white/10 bg-black/20 p-5 text-sm leading-7 text-[#dbe7dd] shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]">{commandPreview}</pre>

          {#if selectedIncident}
            <div class="mt-6 grid gap-3">
              {#each selectedIncident.safe_next_steps.slice(1) as step (step)}
                <div class="mono rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-xs leading-5 text-white/68">
                  {step}
                </div>
              {/each}
            </div>
          {/if}
        </section>
      </section>
    </section>
  </section>
</main>
