plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ke.nyavu.shusha"
    compileSdk = 34

    defaultConfig {
        applicationId = "ke.nyavu.shusha"
        minSdk = 26
        targetSdk = 34
        versionCode = 19
        versionName = "1.3.2"
    }
    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    testOptions {
        unitTests.isIncludeAndroidResources = true
        unitTests.all { it.systemProperty("robolectric.offline", "false") }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")

    // Rendering the screens without a device. The emulator cannot run in this environment:
    // WHPX needs named pipes and software emulation gets no CPU, so the only way to see the
    // interface here is to draw it in the JVM.
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.15.1")
    testImplementation("androidx.test:core:1.6.1")
}
