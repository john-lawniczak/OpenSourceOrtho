package com.opensourceortho.lite

/**
 * Where the lite app reaches the OpenSource Ortho Python engine.
 *
 * The engine is the single source of truth (see ../../API_CONTRACT.md); the app
 * never synthesizes a plan on-device. Change [baseUrl] in one place to point at a
 * deployed engine. Cleartext HTTP is only allowed for the dev hosts in
 * res/xml/network_security_config.xml.
 */
data class EngineConfig(val baseUrl: String) {
    companion object {
        /** Android emulator reaches the developer's host loopback via 10.0.2.2. */
        val EMULATOR = EngineConfig("http://10.0.2.2:8000")

        /** Default used by the app shell. Swap for an https engine in production. */
        val DEFAULT = EMULATOR
    }
}
