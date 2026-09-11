locals {
  class_methods = [
    {"api_mode" = "", "name" = "get_session"},
    {"api_mode" = "", "name" = "list_sessions"},
    {"api_mode" = "", "name" = "create_session"},
    {"api_mode" = "", "name" = "delete_session"},
    {"api_mode" = "async", "name" = "async_get_session"},
    {"api_mode" = "async", "name" = "async_list_sessions"},
    {"api_mode" = "async", "name" = "async_create_session"},
    {"api_mode" = "async", "name" = "async_delete_session"},
    {"api_mode" = "async", "name" = "async_add_session_to_memory"},
    {"api_mode" = "async", "name" = "async_search_memory"},
    {"api_mode" = "stream", "name" = "stream_query"},
    {"api_mode" = "async_stream", "name" = "async_stream_query"},
    {"api_mode" = "async_stream", "name" = "streaming_agent_run_with_events"}
  ]
}

# define the resource with the BYOC configuration, set agent_framework to "google-adk" to enable interactive features on the console.
resource "google_vertex_ai_reasoning_engine" "byoc_weather_agent" {
  display_name = "byoc_weather_agent_tf"
  description  = "BYOC weather agent deployed via Terraform"
  project      = var.project_id
  region       = var.location

  spec {
    class_methods = jsonencode(local.class_methods)
    agent_framework = "google-adk"
    container_spec {
      image_uri = "${var.location}-docker.pkg.dev/${var.project_id}/${var.repository_name}/weather-agent-image:${var.image_tag}"
    }
  }
}