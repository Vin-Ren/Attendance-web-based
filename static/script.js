var debugging = new Map(); //Keys: response,button

function poster(button) {
    debugging.set('button', button);

    $('#4yvftjy34dmt5').remove();
    $("<input />").attr('id', '4yvftjy34dmt5').attr("type", "hidden").attr("name", "status").attr("value", button.value).appendTo("#absenForm");
}

$('#absenForm').submit(function(e){
    e.preventDefault();
    formData = $('#absenForm').serialize();
    $.ajax({
        url: '/input',
        type: 'post',
        data:$('#absenForm').serialize(),
        success:function(retval){
            $('#response-alert').remove();
            if (retval['success']) {
                var alertObj = `<div id="response-alert" class="alert alert-success" role="alert">${retval['success_message']}</div>`;
                $('#timeLimit').prepend(alertObj);
            }
            else {
                var alertObj = `<div id="response-alert" class="alert alert-danger" role="alert">${retval['reason']}</div>`;
                $('#timeLimit').prepend(alertObj);
            }
            debugging.set('response', retval)
        }
    });
});