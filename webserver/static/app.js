$(function() {
  const ENDPOINTS = {
    logsIndex: '/demoapi/logs',
  };

  loadLogs();

  function loadLogs() {
    $('#current_logs').empty();

    $.getJSON(ENDPOINTS.logsIndex, function(data) {
      $('.active_logs_count').text(data.logs.length);

      data.logs.forEach(function(log) {
        addLog(log.name, log.description, log.log_id);
      });
    });
  }

  $('#new_log_button_create').click(function(e) {
    e.preventDefault();

    var name = $('#new_log_name').val();
    var description = $('#new_log_description').val();

    $('.error').hide();

    if (name === '' || description === '') {
      $('.error').show();
      return;
    }

    $.ajax({
      type: 'POST',
      url: ENDPOINTS.logsIndex,
      dataType: 'json',
      contentType: 'application/json',
      async: false,
      data: JSON.stringify({
        name: name,
        description: description,
      }),
      success: function(data) {
        loadLogs();

        $('#new_log_name').val('');
        $('#new_log_description').val('');
      },
    });
  });

  $('body').on('click', '.delete_log', function(e) {
    e.preventDefault();

    if (!confirm('Are you sure?')) {
      return;
    }

    var id = $(this).parent().parent().attr('data-id');

    $.ajax({
      url: ENDPOINTS.logsIndex + '/' + id,
      type: 'DELETE',
      success: function(result) {
        loadLogs();
      }
    });
  });

  function addLog(name, description, id) {
    var template = '<li data-id="{{ ATTR_LOG_ID }}"><h3>Name</h3><p>{{ NAME }}</p><h3>Description</h3><p>{{ DESCRIPTION }}</p><h3>Log ID</h3><p>{{ LOG_ID }}</p><h3>Actions</h3><p><a href="#" class="delete_log">Delete</a></p></li>';

    template = template.replace('{{ ATTR_LOG_ID }}', id);
    template = template.replace('{{ NAME }}', name);
    template = template.replace('{{ DESCRIPTION }}', description);
    template = template.replace('{{ LOG_ID }}', id);

    $('#current_logs').append(template);
  }
});
