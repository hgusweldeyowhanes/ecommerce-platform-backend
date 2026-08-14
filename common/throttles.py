from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle


class BurstAnonThrottle(AnonRateThrottle):
    rate = "60/min"


class BurstUserThrottle(UserRateThrottle):
    rate = "300/min"


class AuthThrottle(ScopedRateThrottle):
    scope = "auth"


class CheckoutThrottle(ScopedRateThrottle):
    scope = "checkout"
