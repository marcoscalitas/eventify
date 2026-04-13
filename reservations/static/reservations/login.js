new JustValidate('#loginForm', { errorLabelCssClass: ['field-error'] })
    .addField('#username', [{ rule: 'required', errorMessage: 'Username is required.' }])
    .addField('#password', [{ rule: 'required', errorMessage: 'Password is required.' }])
    .onSuccess((e) => e.target.submit());
