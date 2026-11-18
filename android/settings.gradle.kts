pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        // The MuPDF JNI bindings (com.artifex.mupdf:fitz) are published only here.
        // Artifex serves this over HTTPS; the plain-http URL in the old 1.15 docs is
        // not used, so no cleartext dependency download is permitted.
        maven {
            name = "ghostscript"
            url = uri("https://maven.ghostscript.com")
            content { includeGroup("com.artifex.mupdf") }
        }
    }
}

rootProject.name = "NextPDF Pro"
include(":app")
