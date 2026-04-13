new JustValidate('#resetConfirmForm', { errorLabelCssClass: ['field-error'], validateBeforeSubmitting: true })
    .addField('#id_new_password1', passwordRules())
    .addField('#id_new_password2', confirmPasswordRules('#id_new_password1'))
    .onSuccess((e) => e.target.submit());
