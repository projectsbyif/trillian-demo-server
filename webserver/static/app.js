$(function() {
  loadLogs();

  function loadLogs() {
    addLog('foo', 'bar', 'baz');
  }

  $('#button_new_log').click(function(e) {
    e.preventDefault();

    var name = $('#new_log_name').val();

    if (name === '') {
      return;
    }

    console.log('create new log with name:', name);

    // On success
    $('#new_log_name').val('');
  });

  $('body').on('click', '.delete_log', function(e) {
    e.preventDefault();

    var uid = $(this).parent().parent().attr('data-uid');

    $(this).parent().parent().remove();
  });

  function addLog(friendlyName, slug, uid) {
    var li = $('<li>');

    li.attr('data-uid', uid);

    var pFriendlyName = $('<p>');
    pFriendlyName.addClass('bold');
    pFriendlyName.text(friendlyName);

    var pSlug = $('<p>');
    pSlug.text(slug);

    var pUniqueId = $('<p>');
    pUniqueId.text(uid);

    var pButtons = $('<p>');

    var aDelete = $('<a>');
    aDelete.attr('href', '#');
    aDelete.addClass('delete_log');
    aDelete.text('Delete');


    pButtons.append(aDelete);

    li.append(pFriendlyName);
    li.append(pSlug);
    li.append(pUniqueId);
    li.append(pButtons);

    $('#current_logs').append(li);
  }
});
