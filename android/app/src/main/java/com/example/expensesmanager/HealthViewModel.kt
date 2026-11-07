package com.example.expensesmanager

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class HealthState { Connecting, Connected, Failed }

class HealthViewModel(
    private val checkHealth: suspend () -> Unit = {
        withContext(Dispatchers.IO) { HealthClient().check() }
    },
) : ViewModel() {
    var state by mutableStateOf(HealthState.Connecting)
        private set

    private var requestInProgress = false

    init {
        connect()
    }

    fun connect() {
        if (requestInProgress) return
        requestInProgress = true
        state = HealthState.Connecting
        viewModelScope.launch {
            try {
                checkHealth()
                state = HealthState.Connected
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                state = HealthState.Failed
            } finally {
                requestInProgress = false
            }
        }
    }
}
