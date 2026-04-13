new JustValidate('#loginForm', { errorLabelCssClass: ['field-error'], validateBeforeSubmitting: true })
    .addField('#email', [
        { rule: 'required', errorMessage: 'Email is required.' },
        { rule: 'email', errorMessage: 'Enter a valid email.' },
    ])
    .addField('#password', passwordRules())
    .onSuccess((e) => {
        e.preventDefault();
        submitForm(e.target);
    });
