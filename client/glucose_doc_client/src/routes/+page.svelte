<!-- src/routes/+page.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { websocketStore, messages, extractedReading, connected } from '$lib/stores/websocket';
	import type { BloodSugarReading } from '$lib/stores/websocket';
	import { fly } from 'svelte/transition';

	let messageInput = '';
	let notesInput = '';
	let messagesContainer: HTMLDivElement;

	// Scroll to bottom when messages update
	function scrollToBottom() {
		if (messagesContainer) {
			setTimeout(() => {
				messagesContainer.scrollTop = messagesContainer.scrollHeight;
			}, 50); // Slight delay to ensure DOM is updated
		}
	}

	$: if ($messages && $messages.length) {
		scrollToBottom();
	}

	// Also scroll after animations complete
	onMount(() => {
		// Initial scroll to bottom
		scrollToBottom();
	});

	function handleSendMessage() {
		if (messageInput.trim()) {
			websocketStore.sendMessage(messageInput.trim());
			messageInput = '';
		}
	}

	function handleConfirmReading() {
		if ($extractedReading) {
			websocketStore.confirmReading($extractedReading, notesInput);
			notesInput = '';
		}
	}

	function handleCancelConfirmation() {
		// Reset the extracted reading in the store
		websocketStore.reset();
	}

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSendMessage();
		}
	}

	onMount(() => {
		if (!$connected) {
			websocketStore.connect();
		}
	});
</script>

<div class="mx-auto max-w-3xl">
	<div class="overflow-hidden rounded-lg bg-white shadow">
		<div class="border-b p-4 sm:p-6">
			<h1 class="text-xl font-bold text-gray-900">Chat with Glucose Buddy</h1>
			<p class="text-sm text-gray-500">Share your blood sugar readings or ask questions</p>
		</div>

		<!-- Messages container -->
		<div class="flex h-96 flex-col overflow-y-auto bg-gray-50 p-4" bind:this={messagesContainer}>
			{#each $messages as message, i}
				<div
					class="{message.fromUser ? 'self-end' : 'self-start'} mb-4 max-w-[75%]"
					in:fly={{ y: 10, duration: 150 }}
					on:introend={scrollToBottom}
				>
					<div
						class="inline-block rounded-lg px-4 py-2 {message.fromUser
							? 'bg-blue-100 text-blue-900'
							: 'border border-gray-200 bg-white shadow-sm'}"
					>
						{message.content}
					</div>
				</div>
			{/each}

			{#if !$connected}
				<div class="rounded-md bg-yellow-50 p-3 text-yellow-800">
					Connecting to server... Please wait.
				</div>
			{/if}
		</div>

		<!-- Reading Confirmation -->
		{#if $extractedReading}
			<div class="border-b border-t bg-blue-50 p-4">
				<h3 class="mb-2 text-lg font-medium text-gray-900">Confirm Your Reading</h3>

				<div class="mb-4 rounded-md border border-blue-200 bg-white p-4 shadow-sm">
					<div class="grid grid-cols-2 gap-3">
						<div>
							<span class="text-sm text-gray-500">Glucose Level</span>
							<p class="text-lg font-bold">{$extractedReading.glucose_level} mg/dL</p>
						</div>
						<div>
							<span class="text-sm text-gray-500">Date</span>
							<p class="text-lg font-medium">{$extractedReading.date}</p>
						</div>
						<div>
							<span class="text-sm text-gray-500">Status</span>
							<p class="text-lg font-medium capitalize">{$extractedReading.meal_status}</p>
						</div>
					</div>
				</div>

				<div class="mb-4">
					<label for="notes" class="label">Additional Notes (optional)</label>
					<textarea
						id="notes"
						bind:value={notesInput}
						class="input h-24 resize-none"
						placeholder="Add any notes about this reading..."
					></textarea>
				</div>

				<div class="flex space-x-3">
					<button class="btn btn-primary" on:click={handleConfirmReading}>Confirm</button>
					<button class="btn btn-secondary" on:click={handleCancelConfirmation}>Cancel</button>
				</div>
			</div>
		{/if}

		<!-- Input area -->
		{#if !$extractedReading}
			<div class="border-t p-4">
				<div class="flex space-x-3">
					<input
						type="text"
						placeholder="Share your blood sugar reading or ask a question..."
						class="input flex-1"
						bind:value={messageInput}
						on:keypress={handleKeyPress}
						disabled={!$connected}
					/>
					<button
						class="btn btn-primary whitespace-nowrap"
						on:click={handleSendMessage}
						disabled={!$connected || !messageInput.trim()}
					>
						Send
					</button>
				</div>
				<p class="mt-2 text-xs text-gray-500">
					Try: "My blood sugar was 120 today after breakfast" or "What's a normal fasting glucose
					level?"
				</p>
			</div>
		{/if}
	</div>
</div>
