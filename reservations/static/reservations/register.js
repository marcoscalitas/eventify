new JustValidate('#registerForm', { errorLabelCssClass: ['field-error'], validateBeforeSubmitting: true })
    .addField('#username', [
        { rule: 'required', errorMessage: 'Username is required.' },
        { rule: 'minLength', value: 3, errorMessage: 'At least 3 characters.' },
        { rule: 'maxLength', value: 150, errorMessage: 'At most 150 characters.' },
    ])
    .addField('#email', [
        { rule: 'required', errorMessage: 'Email is required.' },
        { rule: 'email', errorMessage: 'Enter a valid email.' },
    ])
    .addField('#password', passwordRules())
    .addField('#confirmation', confirmPasswordRules('#password'))
    .addField('#role', [
        { rule: 'required', errorMessage: 'Select a role.' },
    ])
    .onSuccess((e) => {
        e.preventDefault();
        submitForm(e.target);
    });
