package com.example.expensesmanager

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.Button
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModelProvider
import com.example.expensesmanager.ui.theme.ExpensesManagerTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val model = ViewModelProvider(this)[HealthViewModel::class.java]
        enableEdgeToEdge()
        setContent {
            ExpensesManagerTheme {
                HealthScreen(model.state, model::connect)
            }
        }
    }
}

@Composable
fun HealthScreen(
    state: HealthState,
    onRetry: () -> Unit,
) {
    val message = when (state) {
        HealthState.Connecting -> R.string.health_connecting
        HealthState.Connected -> R.string.health_connected
        HealthState.Failed -> R.string.health_failed
    }
    Surface(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.safeDrawingPadding().padding(16.dp)) {
            Text(stringResource(message))
            if (state == HealthState.Failed) {
                Button(onClick = onRetry) { Text(stringResource(R.string.health_retry)) }
            }
        }
    }
}
