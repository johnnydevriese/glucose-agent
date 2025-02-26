<!-- src/routes/history/+page.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { websocketStore, readings, connected } from '$lib/stores/websocket';
	import { format } from 'date-fns';

	// Format date for display
	function formatDate(dateStr: string): string {
		try {
			const date = new Date(dateStr);
			return format(date, 'MMM d, yyyy');
		} catch (e) {
			return dateStr;
		}
	}

	onMount(() => {
		if (!$connected) {
			websocketStore.connect();
		}
		// Request history data when component mounts
		websocketStore.getHistory();
	});
</script>

<div class="mx-auto max-w-4xl">
	<div class="overflow-hidden rounded-lg bg-white shadow">
		<div class="border-b p-4 sm:p-6">
			<h1 class="text-xl font-bold text-gray-900">Blood Sugar History</h1>
			<p class="text-sm text-gray-500">All your recorded readings</p>
		</div>

		<div class="p-4 sm:p-6">
			{#if !$connected}
				<div class="rounded-md bg-yellow-50 p-3 text-yellow-800">
					Connecting to server... Please wait.
				</div>
			{:else if $readings.length === 0}
				<div class="p-6 text-center">
					<div
						class="bg-primary-100 mx-auto flex h-12 w-12 items-center justify-center rounded-full"
					>
						<svg
							class="text-primary-600 h-6 w-6"
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
					</div>
					<h3 class="mt-2 text-sm font-medium text-gray-900">No readings yet</h3>
					<p class="mt-1 text-sm text-gray-500">
						Get started by adding your first blood sugar reading.
					</p>
					<div class="mt-6">
						<a href="/" class="btn btn-primary"> Record a Reading </a>
					</div>
				</div>
			{:else}
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200">
						<thead class="bg-gray-50">
							<tr>
								<th
									scope="col"
									class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
								>
									#
								</th>
								<th
									scope="col"
									class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
								>
									Date
								</th>
								<th
									scope="col"
									class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
								>
									Glucose Level
								</th>
								<th
									scope="col"
									class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
								>
									Status
								</th>
								<th
									scope="col"
									class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
								>
									Notes
								</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 bg-white">
							{#each $readings as reading, i}
								<tr>
									<td class="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
										{i + 1}
									</td>
									<td class="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
										{formatDate(reading.date)}
									</td>
									<td class="whitespace-nowrap px-6 py-4">
										<span
											class="inline-flex rounded-full bg-green-100 px-2 text-xs font-semibold leading-5 text-green-800"
										>
											{reading.glucose_level} mg/dL
										</span>
									</td>
									<td class="whitespace-nowrap px-6 py-4 text-sm capitalize text-gray-500">
										{reading.meal_status}
									</td>
									<td class="max-w-xs break-words px-6 py-4 text-sm text-gray-500">
										{reading.notes || '-'}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
	</div>
</div>
