package com.opensourceortho.lite

import android.content.Context
import android.net.Uri
import java.io.InputStream
import java.security.MessageDigest

data class ScanLayer(val id: String, val mesh: StlMesh, val rotation: List<Float>, val label: String)
data class ScanPresentation(val before: List<ScanLayer>, val after: List<ScanLayer> = emptyList()) {
    fun selecting(arch: String) = if (arch == "Both") this else
        ScanPresentation(before.filter { it.label == arch }, after.filter { it.label == arch })
}

object ScanPresentationLoader {
    fun sample(context: Context, history: SampleHistory, check: () -> Unit): ScanPresentation {
        require(history.visits.size == 2) { "Comparison requires two recorded visits." }
        var vertices = 0
        val visits = history.visits.map { visit ->
            visit.arches.map { arch ->
                check()
                val bytes = context.assets.open("sample-scans/${arch.filename}").use { it.readScanBytes(check) }
                val hash = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
                require(hash == arch.sha256) { "Sample scan failed its integrity check." }
                val mesh = ScanImport.decode(bytes, arch.filename, check)
                vertices += mesh.vertexCount
                require(vertices <= 4_500_000) { "Comparison exceeds the mobile preview limit." }
                ScanLayer(arch.sha256, mesh, arch.displayRotation, arch.name)
            }
        }
        return ScanPresentation(visits[0], visits[1])
    }
    fun imported(context: Context, scans: List<SelectedScan>, check: () -> Unit): ScanPresentation {
        require(scans.isNotEmpty() && scans.size <= 2) { "Choose one or two scans." }
        var vertices = 0
        val layers = scans.map { scan ->
            check()
            val uri = requireNotNull(scan.localUri) { "Choose this file again to preview its geometry." }
            val bytes = context.contentResolver.openInputStream(Uri.parse(uri))?.use { it.readScanBytes(check) }
                ?: error("The selected scan could not be read. Choose the file again.")
            val mesh = ScanImport.decode(bytes, scan.fileName, check)
            vertices += mesh.vertexCount
            require(vertices <= 3_000_000) { "Combined scans exceed the mobile preview limit. View one file at a time." }
            ScanLayer(uri, mesh, listOf(1f,1f,1f), scan.fileName)
        }
        return ScanPresentation(layers)
    }
}

internal fun InputStream.readScanBytes(check: () -> Unit = {}): ByteArray {
    val output = java.io.ByteArrayOutputStream()
    val buffer = ByteArray(262144)
    while (true) {
        check()
        val count = read(buffer)
        if (count < 0) break
        require(count <= StlMesh.MAX_BYTES - output.size()) { "Scan exceeds the mobile preview limit. Open it in the browser." }
        output.write(buffer, 0, count)
    }
    return output.toByteArray()
}
