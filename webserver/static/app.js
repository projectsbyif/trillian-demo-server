$(function() {
  loadLogs();

  function loadLogs() {
    $.getJSON('/demoapi/logs/', function(data) {
      data.logs.forEach(function(log) {
        console.log(log);
        addLog(log.name, log.description, log.log_id);
      });
    });
  }

  $('#new_log_button_create').click(function(e) {
    e.preventDefault();

    var name = $('#new_log_name').val();
    var description = $('#new_log_description').val();

    if (name === '' || description === '') {
      // TODO: Add error message
      return;
    }

    $.ajax({
      type: 'POST',
      url: '/demoapi/logs/',
      dataType: 'json',
      contentType: 'application/json',
      async: false,
      data: JSON.stringify({
        name: name,
        description: description,
      }),
      success: function(data) {
        console.log(data);

        $('#new_log_name').val('');
        $('#new_log_description').val('');
      },
    });
  });

  $('body').on('click', '.delete_log', function(e) {
    e.preventDefault();

    var id = $(this).parent().parent().attr('data-id');

    console.log('/demoapi/logs/' + id + '/');

    $.ajax({
      url: '/demoapi/logs/' + id + '/',
      type: 'DELETE',
      success: function(result) {
        console.log(result);
      }
    });

    //$(this).parent().parent().remove();
  });

  function addLog(name, description, id) {
    var li = $('<li>');

    li.attr('data-id', id);

    var pName = $('<p>');
    pName.addClass('bold');
    pName.text(name);

    var pDescription = $('<p>');
    pDescription.text(description);

    var pId = $('<p>');
    pId.text(id);

    var pButtons = $('<p>');

    var aDelete = $('<a>');
    aDelete.attr('href', '#');
    aDelete.addClass('delete_log');
    aDelete.text('Delete');

    pButtons.append(aDelete);

    li.append(pName);
    li.append(pDescription);
    li.append(pId);
    li.append(pButtons);

    $('#current_logs').append(li);
  }
});
