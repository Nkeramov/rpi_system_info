document.addEventListener('DOMContentLoaded', function() {
    const toggleHeaders = document.querySelectorAll('.toggle-header');
    toggleHeaders.forEach(header => {
        header.addEventListener('click', function() {
            this.classList.toggle('collapsed');
            const content = this.nextElementSibling;
            if (content && content.classList.contains('toggle-content')) {
                content.classList.toggle('collapsed');
            }
        });
    });
});
