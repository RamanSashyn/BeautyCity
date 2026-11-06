"""Короткие обёртки над HTTP-сценарием записи: выбор слота, затем подтверждение."""


def start_booking(client, slot, salon, service, specialist):
    return client.post(
        "/api/book/",
        {
            "slot_id": slot.id,
            "salon_id": salon.id,
            "service_id": service.id,
            "specialist_id": specialist.id,
        },
    )


def confirm_booking(client, name="Мария", phone="+79990001122", question=""):
    return client.post(
        "/api/service-finally/",
        {"fname": name, "tel": phone, "contactsTextarea": question},
    )
