<script>
	// @ts-nocheck
	import { onMount } from 'svelte';
	import { websocketStore, readings, connected } from '$lib/stores/websocket';
	import { format } from 'date-fns';

	function formatDate(dateStr) {
		try {
			const date = new Date(dateStr);
			return format(date, 'MMM d, yyyy');
		} catch {
			return dateStr;
		}
	}

	onMount(() => {
		if (!$connected) {
			websocketStore.connect();
		}
		websocketStore.getHistory();
	});
</script>

<div class="space-y-6">
	<section class="glass-panel-strong rounded-[2rem] p-6 sm:p-8">
		<p class="section-eyebrow mb-2">Reading archive</p>
		<div class="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
			<div>
				<h2 class="font-[var(--font-display)] text-4xl tracking-[-0.04em] text-[var(--ink-strong)]">
					Your glucose history, without spreadsheet fatigue.
				</h2>
				<p class="mt-3 max-w-2xl text-sm leading-7 text-[var(--ink-soft)]">
					A clean ledger of readings, meal context, and notes so it is easy to spot patterns
					or remember what was different on a given day.
				</p>
			</div>
			<div class="metric-card min-w-[12rem]">
				<p class="metric-label">Total entries</p>
				<p class="metric-value mt-3">{$readings.length}</p>
			</div>
		</div>
	</section>

	<section class="glass-panel-strong overflow-hidden rounded-[2rem]">
		{#if !$connected}
			<div class="p-6">
				<div class="rounded-2xl border border-[rgba(176,114,45,0.18)] bg-[rgba(255,248,235,0.86)] p-4 text-sm text-[var(--warning)]">
					Connecting to server... Please wait.
				</div>
			</div>
		{:else if $readings.length === 0}
			<div class="p-8 text-center sm:p-12">
				<div class="mx-auto flex h-16 w-16 items-center justify-center rounded-[1.5rem] bg-[rgba(184,82,67,0.1)] text-2xl">
					<span aria-hidden="true">◌</span>
				</div>
				<h3 class="mt-5 font-[var(--font-display)] text-3xl tracking-[-0.03em] text-[var(--ink-strong)]">
					No readings yet
				</h3>
				<p class="mx-auto mt-3 max-w-md text-sm leading-7 text-[var(--ink-soft)]">
					Start with a single reading and this archive will turn into a much more useful story of
					your routine.
				</p>
				<div class="mt-6">
					<a href="/" class="btn btn-primary">Record a Reading</a>
				</div>
			</div>
		{:else}
			<div class="overflow-x-auto">
				<table class="min-w-full">
					<thead>
						<tr class="border-b border-[rgba(125,84,76,0.12)] text-left">
							<th class="px-5 py-4 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">Date</th>
							<th class="px-5 py-4 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">Reading</th>
							<th class="px-5 py-4 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">Context</th>
							<th class="px-5 py-4 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ink-soft)]">Notes</th>
						</tr>
					</thead>
					<tbody>
						{#each [...$readings].reverse() as reading}
							<tr class="border-b border-[rgba(125,84,76,0.08)] align-top">
								<td class="px-5 py-5">
									<p class="font-semibold text-[var(--ink-strong)]">{formatDate(reading.date)}</p>
									<p class="mt-1 text-xs uppercase tracking-[0.16em] text-[var(--ink-soft)]">
										{reading.date}
									</p>
								</td>
								<td class="px-5 py-5">
									<div class="inline-flex rounded-full bg-[rgba(59,127,107,0.12)] px-4 py-2 text-sm font-semibold text-[var(--success)]">
										{reading.glucose_level} mg/dL
									</div>
								</td>
								<td class="px-5 py-5">
									<span class="status-chip {reading.meal_status === 'fasting' ? 'status-chip-success' : 'status-chip-warning'} capitalize">
										{reading.meal_status}
									</span>
								</td>
								<td class="max-w-md px-5 py-5 text-sm leading-7 text-[var(--ink-soft)]">
									{reading.notes || 'No notes attached to this reading.'}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
</div>
