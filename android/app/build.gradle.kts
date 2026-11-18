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
        versionCode = 11
        versionName = "0.9.2"
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
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
}
