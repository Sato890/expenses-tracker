package com.example.expensesmanager

import java.io.IOException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HealthViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() { Dispatchers.setMain(dispatcher) }

    @After
    fun tearDown() { Dispatchers.resetMain() }

    @Test
    fun successfulRequestShowsConnected() = runTest(dispatcher) {
        val model = HealthViewModel {}
        assertEquals(HealthState.Connecting, model.state)
        runCurrent()
        assertEquals(HealthState.Connected, model.state)
    }

    @Test
    fun retryRecoversFromFailedRequest() = runTest(dispatcher) {
        var fail = true
        val model = HealthViewModel { if (fail) throw IOException("Offline") }
        runCurrent()
        assertEquals(HealthState.Failed, model.state)
        fail = false
        model.connect()
        assertEquals(HealthState.Connecting, model.state)
        runCurrent()
        assertEquals(HealthState.Connected, model.state)
    }

    @Test
    fun repeatedRetryDoesNotStartOverlappingRequests() = runTest(dispatcher) {
        val response = CompletableDeferred<Unit>()
        var calls = 0
        val model = HealthViewModel { calls++; response.await() }
        runCurrent()
        model.connect()
        runCurrent()
        assertEquals(1, calls)
        response.complete(Unit)
        runCurrent()
        assertEquals(HealthState.Connected, model.state)
    }
}
