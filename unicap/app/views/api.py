"""The REST API: capacity from numbers only (no chapter rows are read or written).

Authenticated by a logged-in session or a JWT (`POST /api/token/` with a username and a
password; send `Authorization: Bearer <access>`).
"""

from django.contrib.auth.decorators import login_not_required
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from unicap.domain import DomainError, evaluate_numbers

from ..serializers import CalculationRequestSerializer, report_data
from ..texts import error_text


@login_not_required  # DRF authenticates (session or JWT): the login page is for browsers
@api_view(["POST"])
def calculate(request: Request) -> Response:
    """Calculate a chapter's capacity from numbers.

    Example:
        ```json
        POST /api/capacity/calculate/
        {
          "max_students": 900,
          "faculties": [{
            "name": "Dentistry", "students_per_phd": 10, "current_students": 120,
            "specializations": [
              {"name": "Dentistry", "type": "specialized", "max_percentage": 70,
               "fulltime_staff": 6, "fulltime_borrowed": 2, "parttime": 3, "masters": 2},
              {"name": "Biology", "type": "supported", "fulltime_staff": 2}
            ]
          }]
        }
        ```
    """
    serializer = CalculationRequestSerializer(data=request.data)

    serializer.is_valid(raise_exception=True)

    try:
        report = evaluate_numbers(
            serializer.faculty_numbers(),
            max_students=serializer.validated_data.get("max_students"),
            count=serializer.validated_data["count"],
        )
    except DomainError as error:
        body = {"detail": error_text(error), "code": str(error.code) if error.code else None}
        return Response(body, status=status.HTTP_400_BAD_REQUEST)

    return Response(report_data(report))
