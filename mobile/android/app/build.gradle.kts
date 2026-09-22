plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.kotlin.plugin.serialization")
}

android {
    namespace = "com.opensourceortho.lite"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.opensourceortho.lite"
        minSdk = 26
        targetSdk = 34
        versionCode = 4
        versionName = "0.4.0-scaffold"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    sourceSets.getByName("main").assets.srcDir("../../sample-history")

    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/sample-scans"))

    buildFeatures {
        buildConfig = true
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.09.03")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    debugImplementation("androidx.compose.ui:ui-tooling")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
}

// Bundle only the four public STL originals; never copy the entire case directory.
val bundleSampleScans by tasks.registering(Sync::class) {
    val historyFile = file("../../sample-history/history.json")
    inputs.file(historyFile)
    val history = groovy.json.JsonSlurper().parse(historyFile) as Map<*, *>
    val visits = history["visits"] as List<Map<*, *>>
    val names = visits.flatMap { it["arches"] as List<Map<*, *>> }.map { it["filename"] as String }
    from(file("../../../datasets/${history["specimenId"]}")) { include(names) }
    into(layout.buildDirectory.dir("generated/sample-scans/sample-scans"))
    doLast {
        check(names.all { destinationDir.resolve(it).isFile }) { "Missing canonical sample STL" }
    }
}
tasks.named("preBuild") { dependsOn(bundleSampleScans) }
