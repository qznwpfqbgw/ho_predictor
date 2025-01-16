#include <gio/gio.h>
#include <glib.h>
#include <glib/gprintf.h>
#include <libqmi-glib/libqmi-glib.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
struct timeval tv;
static GMainLoop *loop;
static GCancellable *cancellable;
static QmiDevice *device;
static QmiService service;
static QmiClient *client;
static gboolean operation_status;

static gchar *client_cid_str;
static gchar *device_str;
static gboolean client_no_release_cid_flag;
static gchar *lte_band_str = 0; //  LTE bands

/* Context */
typedef struct {
  QmiDevice *device;
  QmiClientNas *client;
  GCancellable *cancellable;
} Context;
static Context *ctx;

static GOptionEntry main_entries[] = {
    {"device", 'd', 0, G_OPTION_ARG_STRING, &device_str, "Specify device path",
     "[PATH]"},
    {"client-cid", 'c', 0, G_OPTION_ARG_STRING, &client_cid_str,
     "Use the given CID, don't allocate a new one", "[CID]"},
    {"client-no-release-cid", 0, 0, G_OPTION_ARG_NONE,
     &client_no_release_cid_flag, "Do not release the CID when exiting", NULL},
     {"lte-band", 'l', 0, G_OPTION_ARG_STRING, &lte_band_str, "Set LTE bands as a comma-separated list (e.g., 1,3,7,8)", "[BANDS]"},
    NULL
};

static void signals_handler(int signum) {
  if (loop && g_main_loop_is_running(loop)) {
    g_printerr("%s\n", "cancelling the main loop...\n");
    g_main_loop_quit(loop);
  }
}

// Helper function to parse LTE bands from string
static QmiNasLteBandPreference parse_lte_bands(const gchar *band_str) {
    QmiNasLteBandPreference lte_band_preference = 0;
    gchar **bands = g_strsplit(band_str, ",", -1);
    for (gchar **band = bands; *band; band++) {
        guint32 band_num = atoi(*band);
        if (band_num > 0 && band_num <= 64) {
            lte_band_preference |= (1ULL << (band_num - 1)); // LTE band bit mapping
        } else {
            g_printerr("error: invalid LTE band number: %s\n", *band);
        }
    }
    g_strfreev(bands);
    return lte_band_preference;
}

static void set_system_selection_preference_ready(QmiClientNas *client,
                                                  GAsyncResult *res) {
  QmiMessageNasSetSystemSelectionPreferenceOutput *output = NULL;
  GError *error = NULL;

  output = qmi_client_nas_set_system_selection_preference_finish(client, res,
                                                                 &error);
  if (!output) {
    g_printerr("error: operation failed: %s\n", error->message);
    g_error_free(error);
    g_main_loop_quit(loop);
    return;
  }

  if (!qmi_message_nas_set_system_selection_preference_output_get_result(
          output, &error)) {
    g_printerr("error: couldn't set operating mode: %s\n", error->message);
    g_error_free(error);
    qmi_message_nas_set_system_selection_preference_output_unref(output);
    g_main_loop_quit(loop);
    return;
  }

  g_print("[%s] System selection preference set successfully; replug your "
          "device.\n",
          qmi_device_get_path_display(ctx->device));

  qmi_message_nas_set_system_selection_preference_output_unref(output);

  g_main_loop_quit(loop);
}

void qmicli_nas_run(QmiDevice *device, QmiClientNas *client,
                    GCancellable *cancellable) {
  /* Initialize context */
  ctx = g_slice_new(Context);
  ctx->device = g_object_ref(device);
  ctx->client = g_object_ref(client);
  if (cancellable)
    ctx->cancellable = g_object_ref(cancellable);
  QmiMessageNasSetSystemSelectionPreferenceInput *input;
  input = qmi_message_nas_set_system_selection_preference_input_new();
  QmiNasLteBandPreference qmi_lte_bands = parse_lte_bands(lte_band_str);
  // QMI_NAS_LTE_BAND_PREFERENCE_EUTRAN_1 ;
  qmi_message_nas_set_system_selection_preference_input_set_lte_band_preference(
      input, qmi_lte_bands, NULL);
  // qmi_message_nas_set_system_selection_preference_input_set_nr5g_nsa_band_preference
  // ( 	input, 	qmi_nr5g_bands[0], 	qmi_nr5g_bands[1],static gchar
  // *device_set_instance_id_str; 	qmi_nr5g_bands[2],
  // qmi_nr5g_bands[3], 	qmi_nr5g_bands[4], 	qmi_nr5g_bands[5],
  // qmi_nr5g_bands[6], 	qmi_nr5g_bands[7], 	NULL);
  qmi_client_nas_set_system_selection_preference(
      ctx->client, input, 10, ctx->cancellable,
      (GAsyncReadyCallback)set_system_selection_preference_ready, NULL);
  qmi_message_nas_set_system_selection_preference_input_unref(input);
  return;
  g_warn_if_reached();
}

static void allocate_client_ready(QmiDevice *dev, GAsyncResult *res) {
  GError *error = NULL;

  client = qmi_device_allocate_client_finish(dev, res, &error);
  if (!client) {
    g_printerr("error: couldn't create client for the '%s' service: %s\n",
               qmi_service_get_string(service), error->message);
    exit(EXIT_FAILURE);
  }

  /* Run the service-specific action */
  qmicli_nas_run(dev, QMI_CLIENT_NAS(client), cancellable);
}

static void device_allocate_client(QmiDevice *dev) {
  guint8 cid = QMI_CID_NONE;
  if (client_cid_str) {
    guint32 cid32;

    cid32 = atoi(client_cid_str);
    if (!cid32 || cid32 > G_MAXUINT8) {
      g_printerr("error: invalid CID given '%s'\n", client_cid_str);
      exit(EXIT_FAILURE);
    }

    cid = (guint8)cid32;
    g_debug("Reusing CID '%u'", cid);
  }
  /* As soon as we get the QmiDevice, create a client for the requested
   * service */
  qmi_device_allocate_client(dev, service, cid, 10, cancellable,
                             (GAsyncReadyCallback)allocate_client_ready, NULL);
}

static void device_open_ready(QmiDevice *dev, GAsyncResult *res) {
  GError *error = NULL;

  if (!qmi_device_open_finish(dev, res, &error)) {
    g_printerr("error: couldn't open the QmiDevice: %s\n", error->message);
    exit(EXIT_FAILURE);
  }

  g_debug("QMI Device at '%s' ready", qmi_device_get_path_display(dev));

  device_allocate_client(dev);
}

static void device_new_ready(GObject *unused, GAsyncResult *res) {
  QmiDeviceOpenFlags open_flags = QMI_DEVICE_OPEN_FLAGS_NONE;
  GError *error = NULL;

  device = qmi_device_new_finish(res, &error);
  if (!device) {
    g_printerr("error: couldn't create QmiDevice: %s\n", error->message);
    exit(EXIT_FAILURE);
  }

  /* Open the device */
  qmi_device_open(device, open_flags, 15, cancellable,
                  (GAsyncReadyCallback)device_open_ready, NULL);
}

int main(int argc, char **argv) {
  gettimeofday(&tv,NULL);
  g_print("start %ld.%ld\n", tv.tv_sec, tv.tv_usec);
  GError *error = NULL;
  GFile *file;

  GOptionContext *context;
  context = g_option_context_new("- Control QMI devices");
  g_option_context_add_main_entries(context, main_entries, NULL);
  if (!g_option_context_parse(context, &argc, &argv, &error)) {
    g_printerr("error: %s\n", error->message);
    exit(EXIT_FAILURE);
  }
  g_option_context_free(context);
  if (!device_str) {
    g_printerr("error: no device path and client id specified\n");
    exit(EXIT_FAILURE);
  }
  file = g_file_new_for_commandline_arg(device_str);
  /* Setup signals */
  signal(SIGINT, signals_handler);
  signal(SIGHUP, signals_handler);
  signal(SIGTERM, signals_handler);
  service = QMI_SERVICE_NAS;
  /* Create requirements for async options */
  cancellable = g_cancellable_new();
  loop = g_main_loop_new(NULL, FALSE);

  /* Launch QmiDevice creation */
  qmi_device_new(file, cancellable, (GAsyncReadyCallback)device_new_ready,
                 GUINT_TO_POINTER(service));
  g_main_loop_run(loop);

  if (cancellable)
    g_object_unref(cancellable);
  if (client)
    g_object_unref(client);
  if (device)
    g_object_unref(device);
  g_main_loop_unref(loop);
  g_object_unref(file);

  return EXIT_SUCCESS;
}
