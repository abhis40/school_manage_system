(function($) {
    $(document).ready(function() {
        function toggleStreamField() {
            var classLevel = $('#id_class_level').val();
            var streamField = $('.field-stream');
            
            if (classLevel === '11' || classLevel === '12') {
                streamField.show();
            } else {
                streamField.hide();
                $('#id_stream').val('');
            }
        }

        $('#id_class_level').change(toggleStreamField);
        toggleStreamField(); // Run on page load
    });
})(django.jQuery); 