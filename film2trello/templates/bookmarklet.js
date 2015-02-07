(function() {
    var url, form, textarea;

    form = document.createElement('form');
    form.method = 'POST';
    form.action = '{{ url }}?nocache=' + Math.random();

    textarea = document.createElement('textarea');
    textarea.name = 'url';
    textarea.value = window.location.href;

    form.appendChild(textarea);
    document.body.appendChild(form);

    form.submit();
})()
