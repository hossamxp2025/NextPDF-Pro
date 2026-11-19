import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

// ---------------------------------------------------------------- upload key
//
// Google Play signs the app with a key it holds; what is uploaded is signed
// with an *upload* key, which only proves the upload came from us. That key
// still matters: lose it and a new one has to be registered with Play before
// another update can be uploaded, so it is backed up, and it never enters git.
//
// Its details live in android/keystore.properties, which .gitignore excludes.
// Nothing here has a default password and nothing falls back to a key checked
// into the repository: without that file the release build is simply left
// unsigned, which fails loudly at upload time rather than quietly shipping
// something signed by a key everyone can read.
val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties().apply {
    if (keystorePropertiesFile.isFile) {
        keystorePropertiesFile.inputStream().use { load(it) }
    }
}

fun keystoreEntry(name: String): String? =
    keystoreProperties.getProperty(name)?.trim()?.takeIf { it.isNotEmpty() }

val uploadKeystore = keystoreEntry("storeFile")?.let { path ->
    val asGiven = File(path)
    if (asGiven.isAbsolute) asGiven else rootProject.file(path)
}
val hasUploadKey = uploadKeystore?.isFile == true &&
    keystoreEntry("storePassword") != null &&
    keystoreEntry("keyAlias") != null &&
    keystoreEntry("keyPassword") != null

if (!hasUploadKey) {
    logger.lifecycle(
        "NextPDF: no upload key configured, so a release build will be " +
            "UNSIGNED. See android/README.md to create one."
    )
}

android {
    namespace = "com.futureautomation.nextpdf"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.futureautomation.nextpdf"
        minSdk = 24
        targetSdk = 35
        // Deliberately 0.1.0 and not 1.6.1: this app shares the desktop engine and
        // the desktop rules, not its feature set. See docs/ANDROID_PLAN.md.
        versionCode = 3
        versionName = "0.2.1"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        ndk {
            // The MuPDF AAR carries arm64-v8a, armeabi-v7a, x86 and x86_64. Keeping
            // the list explicit stops a silently missing native library from
            // reaching a device; x86_64 is here so an emulator can run the
            // instrumented tests. 32-bit x86 is left out — no such phone ships.
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
        }
    }

    signingConfigs {
        if (hasUploadKey) {
            create("upload") {
                storeFile = uploadKeystore
                storePassword = keystoreEntry("storePassword")
                keyAlias = keystoreEntry("keyAlias")
                keyPassword = keystoreEntry("keyPassword")
                // Both schemes: v1 for Android 6 and older, which minSdk 24
                // still includes, v2 for everything after.
                enableV1Signing = true
                enableV2Signing = true
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            signingConfig =
                if (hasUploadKey) signingConfigs.getByName("upload") else null
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        // Off by default since AGP 8; the About screen shows the real versionName
        // rather than a string copied by hand that could drift from it.
        buildConfig = true
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons.extended)

    implementation(libs.mupdf.fitz)

    testImplementation(libs.junit)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
}
