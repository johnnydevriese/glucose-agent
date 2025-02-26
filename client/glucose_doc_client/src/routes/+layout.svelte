<script>
	import '../app.css';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
</script>

<div class="min-h-screen bg-gray-50">
	<nav class="bg-white shadow-md">
		<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 items-center justify-between">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<span class="text-2xl font-bold text-black">🩸 Glucose Buddy</span>
						</div>
						<div class="hidden md:block">
							<div class="ml-10 flex items-baseline space-x-4">
								<a
									href="/"
									class="rounded-md px-3 py-2 text-sm font-medium text-black hover:bg-gray-200"
									aria-current={$page.url.pathname === '/' ? 'page' : undefined}
									class:bg-gray-300={$page.url.pathname === '/'}
								>
									Chat
								</a>
								<a
									href="/history"
									class="rounded-md px-3 py-2 text-sm font-medium text-black hover:bg-gray-200"
									aria-current={$page.url.pathname === '/history' ? 'page' : undefined}
									class:bg-gray-300={$page.url.pathname === '/history'}
								>
									History
								</a>
								<a
									href="/stats"
									class="rounded-md px-3 py-2 text-sm font-medium text-black hover:bg-gray-200"
									aria-current={$page.url.pathname === '/stats' ? 'page' : undefined}
									class:bg-gray-300={$page.url.pathname === '/stats'}
								>
									Statistics
								</a>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</nav>
	<main class="py-10">
		<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
			<slot></slot>
		</div>
	</main>
	<footer class="bg-white">
		<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
			<p class="text-center text-sm text-gray-500">
				&copy; 2025 Glucose Buddy. Keep track of your health.
			</p>
		</div>
	</footer>
</div>
